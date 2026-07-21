import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend - must be before pyplot import
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
import os
import gc

# ---------------------------------------------------------------------------
# Chart styling - matches the PDF color palette
# ---------------------------------------------------------------------------
PALETTE = ['#2e7d9e', '#3d9a8a', '#5b7fa6', '#6cb2c1', '#4a7eb5', '#2d8a7a', '#7aa3c0']
PIE_PALETTE = PALETTE + ['#94a3b8', '#64748b', '#475569', '#334155']

sns.set_style("white")
plt.rcParams.update({
    'figure.figsize': (9, 5),
    'figure.max_open_warning': 0,
    'agg.path.chunksize': 10000,
})

AGE_GROUP_KEYS = ('Adult', 'Sub-Adult', 'Calf', 'Unidentified')


def _style_chart(ax, fig):
    """Apply consistent, clean styling to a chart axis."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e2e8f0')
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(colors='#4a5568', labelsize=9.5)
    ax.xaxis.label.set_color('#4a5568')
    ax.yaxis.label.set_color('#4a5568')
    ax.title.set_color('#1a3a5c')
    ax.set_facecolor('#f8fafc')
    fig.patch.set_facecolor('white')
    ax.yaxis.grid(True, color='#e2e8f0', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def _style_pie(ax, fig):
    """Apply consistent styling to pie charts."""
    ax.set_facecolor('#f8fafc')
    fig.patch.set_facecolor('white')


def _add_value_labels(ax, bars):
    """Add formatted count labels above each bar."""
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.annotate(
                f'{int(h):,}',
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords='offset points',
                ha='center', va='bottom',
                fontsize=8.5, color='#4a5568', fontweight='bold',
            )


def _num(value):
    """Coerce numeric counts from ints or nested dict values."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        return sum(_num(v) for v in value.values())
    return 0


def _normalize_list(value):
    """Return a flat list of non-empty scalar values."""
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, '', [])]
    return [value]


def _get_obs_field(obs, *keys):
    """Return the first populated observation field from a list of keys."""
    for key in keys:
        value = obs.get(key)
        if value not in (None, '', []):
            return value
    return None


def _format_label(value):
    return str(value).replace('_', ' ').title()


def _counts_to_rows(counts, include_share=True):
    """Convert a Counter-like mapping to sorted table rows."""
    total = sum(counts.values())
    rows = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    # Share column disabled for all report tables — keep Count only.
    # if not include_share or total == 0:
    #     return [(label, count) for label, count in rows]
    # return [
    #     (label, count, round(count / total * 100, 1))
    #     for label, count in rows
    # ]
    return [(label, count) for label, count in rows]


def _share_rows(rows):
    """Attach share values to (label, count) rows."""
    # Share column disabled for all report tables — keep Count only.
    # total = sum(row[1] for row in rows)
    # if total == 0:
    #     return [(label, count, 0.0) for label, count in rows]
    # return [(label, count, round(count / total * 100, 1)) for label, count in rows]
    return [(label, count) for label, count in rows]


def _limit_pie_slices(counts, max_slices=8):
    """Keep the largest categories and group the remainder as Other."""
    rows = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    if len(rows) <= max_slices:
        return dict(rows)

    visible = rows[: max_slices - 1]
    other_total = sum(count for _, count in rows[max_slices - 1 :])
    if other_total:
        visible.append(('Other', other_total))
    return dict(visible)


def _species_animal_total(species_entry):
    """Total animals recorded for one species entry."""
    sp = species_entry
    total = (
        _num(sp.get('adult'))
        + _num(sp.get('adultMale'))
        + _num(sp.get('adultFemale'))
        + _num(sp.get('subAdult'))
        + _num(sp.get('calf'))
        + _num(sp.get('calves'))
        + _num(sp.get('unidentified'))
    )
    if total > 0:
        return total
    return 1


def _species_age_counts(species_entry):
    """Return age-group counts for one species entry."""
    sp = species_entry
    return {
        'Adult': _num(sp.get('adult')) + _num(sp.get('adultMale')) + _num(sp.get('adultFemale')),
        'Sub-Adult': _num(sp.get('subAdult')),
        'Calf': _num(sp.get('calf')) + _num(sp.get('calves')),
        'Unidentified': _num(sp.get('unidentified')),
    }


def _collect_species_metrics(observations):
    """Aggregate species totals and age composition across observations."""
    species_totals = Counter()
    species_age = defaultdict(lambda: Counter())

    for obs in observations:
        for sp in obs.get('species', []):
            species_type = sp.get('type', 'Unknown')
            age_counts = _species_age_counts(sp)
            total = sum(age_counts.values()) or 1
            species_totals[species_type] += total
            for age_group, count in age_counts.items():
                if count:
                    species_age[species_type][age_group] += count

    return species_totals, species_age


def _collect_species_by_dimension(observations, field_keys, fallback_label='Not Recorded'):
    """Count species sightings grouped by an observation-level dimension.

    Each species entry within an observation counts as one sighting, matching
    the report's total record count rather than summing animal headcounts.
    """
    grouped = defaultdict(Counter)

    for obs in observations:
        raw_value = _get_obs_field(obs, *field_keys)
        values = _normalize_list(raw_value) or [fallback_label]
        species_list = obs.get('species', [])

        if species_list:
            for sp in species_list:
                species_type = sp.get('type', 'Unknown')
                for value in values:
                    grouped[value][species_type] += 1
        else:
            for value in values:
                grouped[value]['Unknown'] += 1

    return grouped


def _collect_location_counts(observations):
    """Count sightings by site, ghat, or village fields."""
    location_counts = Counter()

    for obs in observations:
        location = _get_obs_field(
            obs,
            'site',
            'siteName',
            'ghat',
            'ghats',
            'village',
            'location',
            'locationName',
        )
        if location:
            if isinstance(location, list):
                for item in location:
                    location_counts[item] += 1
            else:
                location_counts[location] += 1

    return location_counts


def _collect_disturbance_counts(observations):
    """Count disturbance records from dedicated or legacy threat fields."""
    counts = Counter()

    for obs in observations:
        values = _normalize_list(_get_obs_field(obs, 'disturbances', 'disturbance'))
        if not values:
            values = _normalize_list(obs.get('threats', []))
        counts.update(values)

    return counts


def _collect_fishing_gear_counts(observations):
    """Count fishing gear types from supported field names."""
    counts = Counter()

    for obs in observations:
        values = _normalize_list(
            _get_obs_field(
                obs,
                'fishingGear',
                'fishingGearTypes',
                'gearTypes',
                'gear',
            )
        )
        counts.update(values)

    return counts


def _save_figure(fig, chart_path):
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    gc.collect()


def _append_summary(chart_files, summary_data, chart_path, title, rows, columns=None):
    chart_files.append(chart_path)
    summary_data.append({
        'title': title,
        # Share column disabled for all report tables.
        # 'columns': columns or ['Category', 'Count', 'Share'],
        'columns': columns or ['Category', 'Count'],
        'data': rows,
    })


def _create_bar_chart(
    output_folder,
    filename,
    title,
    counts,
    xlabel,
    ylabel='Number of Sightings',
    # include_share=True,  # Share column disabled for all report tables.
    include_share=False,
):
    if not counts:
        return None, None

    rows = _counts_to_rows(counts, include_share=include_share)
    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, width=0.4, color=PALETTE[1])
    ax.set_xlabel(xlabel, fontsize=10, labelpad=10)
    ax.set_ylabel(ylabel, fontsize=10, labelpad=10)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
    _style_chart(ax, fig)
    _add_value_labels(ax, bars)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    chart_path = os.path.join(output_folder, filename)
    _save_figure(fig, chart_path)
    return chart_path, rows


def _spread_label_positions(natural_ys, y_min, y_max, min_spacing):
    """Spread label y-positions so they do not overlap within a side."""
    if not natural_ys:
        return []

    indexed = sorted(enumerate(natural_ys), key=lambda item: item[1])
    count = len(indexed)
    if count == 1:
        return [natural_ys[0]]

    available = y_max - y_min
    spacing = min(min_spacing, available / max(count - 1, 1))

    ordered_indices = [idx for idx, _ in indexed]
    ordered_values = [value for _, value in indexed]
    positions = ordered_values[:]

    for i in range(1, count):
        positions[i] = max(positions[i], positions[i - 1] + spacing)

    overflow = positions[-1] - y_max
    if overflow > 0:
        positions = [value - overflow for value in positions]

    underflow = y_min - positions[0]
    if underflow > 0:
        positions = [value + underflow for value in positions]

    if positions[-1] - positions[0] > available:
        positions = [
            y_min + (available * i / (count - 1))
            for i in range(count)
        ]

    resolved = [0.0] * count
    for idx, position in zip(ordered_indices, positions):
        resolved[idx] = position
    return resolved


def _draw_pie_callouts(ax, wedges, labels, values, total, pie_radius):
    """Draw non-overlapping pie callouts grouped by chart side."""
    text_x_right = 1.38
    text_x_left = -1.38
    y_min, y_max = -1.55, 1.55
    min_spacing = 0.11
    radial_gap = 0.08

    left_items = []
    right_items = []

    for wedge, label, value in zip(wedges, labels, values):
        share = value / total * 100
        angle = (wedge.theta2 - wedge.theta1) / 2.0 + wedge.theta1
        rad = np.deg2rad(angle)
        x = np.cos(rad)
        y = np.sin(rad)
        item = {
            'label': label,
            'share': share,
            'x_edge': pie_radius * x,
            'y_edge': pie_radius * y,
            'x_elbow': (pie_radius + radial_gap) * x,
            'y_elbow': pie_radius * y,
            'y_natural': pie_radius * y,
        }
        if x >= 0:
            right_items.append(item)
        else:
            left_items.append(item)

    for side_items, text_x, ha, text_offset in (
        (right_items, text_x_right, 'left', 0.04),
        (left_items, text_x_left, 'right', -0.04),
    ):
        if not side_items:
            continue

        spread_ys = _spread_label_positions(
            [item['y_natural'] for item in side_items],
            y_min,
            y_max,
            min_spacing,
        )
        for item, y_text in zip(side_items, spread_ys):
            item['x_text'] = text_x
            item['y_text'] = y_text
            item['ha'] = ha
            item['text_offset'] = text_offset

            ax.plot(
                [item['x_edge'], item['x_elbow'], text_x, text_x],
                [item['y_edge'], item['y_elbow'], item['y_elbow'], y_text],
                color='#94a3b8',
                lw=0.9,
                solid_capstyle='round',
                zorder=0,
            )
            ax.text(
                text_x + text_offset,
                y_text,
                f'{item["label"]} ({item["share"]:.1f})',
                ha=ha,
                va='center',
                fontsize=8.5,
                color='#1a3a5c',
                zorder=1,
            )


def _create_pie_chart(output_folder, filename, title, counts, max_slices=8):
    if not counts:
        return None, None

    pie_counts = _limit_pie_slices(counts, max_slices=max_slices)
    rows = _counts_to_rows(pie_counts)
    labels = [_format_label(label) for label in pie_counts.keys()]
    values = list(pie_counts.values())
    total = sum(values)
    colors = PIE_PALETTE[: len(labels)]
    pie_radius = 0.62

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, _, autotexts = ax.pie(
        values,
        labels=None,
        autopct=lambda pct: f'{pct:.1f}' if pct >= 10 else '',
        startangle=90,
        counterclock=False,
        colors=colors,
        radius=pie_radius,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.2, 'antialiased': True},
        pctdistance=0.72,
        textprops={'fontsize': 8.5, 'color': '#1a3a5c', 'fontweight': 'bold'},
    )
    for autotext in autotexts:
        if autotext.get_text():
            autotext.set_color('#1a3a5c')
            autotext.set_fontweight('bold')

    _draw_pie_callouts(ax, wedges, labels, values, total, pie_radius)

    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(-1.68, 1.68)
    ax.set_ylim(-1.68, 1.68)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=12, color='#1a3a5c')
    _style_pie(ax, fig)
    fig.subplots_adjust(top=0.9, left=0.01, right=0.99, bottom=0.01)

    chart_path = os.path.join(output_folder, filename)
    _save_figure(fig, chart_path)
    return chart_path, rows


def _create_stacked_bar_chart(
    output_folder,
    filename,
    title,
    grouped_counts,
    xlabel,
    ylabel='Number of Animals',
    stack_order=None,
):
    """Create a stacked bar chart from {category: Counter(subcategory)}."""
    if not grouped_counts:
        return None, None

    categories = sorted(grouped_counts.keys(), key=lambda key: sum(grouped_counts[key].values()), reverse=True)
    if stack_order is None:
        stack_keys = sorted(
            {key for counter in grouped_counts.values() for key in counter.keys()},
            key=lambda key: sum(grouped_counts[cat].get(key, 0) for cat in categories),
            reverse=True,
        )
    else:
        stack_keys = list(stack_order)

    fig, ax = plt.subplots(figsize=(10, 5))
    bottoms = [0] * len(categories)

    for index, stack_key in enumerate(stack_keys):
        values = [grouped_counts[category].get(stack_key, 0) for category in categories]
        if not any(values):
            continue
        ax.bar(
            categories,
            values,
            bottom=bottoms,
            label=_format_label(stack_key),
            color=PIE_PALETTE[index % len(PIE_PALETTE)],
            width=0.55,
        )
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]

    ax.set_xlabel(xlabel, fontsize=10, labelpad=10)
    ax.set_ylabel(ylabel, fontsize=10, labelpad=10)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
    _style_chart(ax, fig)
    ax.legend(loc='upper right', fontsize=8, frameon=False)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    chart_path = os.path.join(output_folder, filename)
    _save_figure(fig, chart_path)

    table_rows = []
    for category in categories:
        total = sum(grouped_counts[category].values())
        if total == 0:
            continue
        for stack_key in stack_keys:
            count = grouped_counts[category].get(stack_key, 0)
            if count:
                # Share column disabled for all report tables.
                # share = round(count / total * 100, 1)
                # table_rows.append((f'{_format_label(category)} - {_format_label(stack_key)}', count, share))
                table_rows.append((f'{_format_label(category)} - {_format_label(stack_key)}', count))

    return chart_path, table_rows


def _district_breakdown_rows(observations):
    """Build per-district geography rows for the detailed table.

    Returns a tuple of (rows, row_types) where row_types is a list of
    'detail' or 'total' strings aligned with each row in rows.
    """
    district_counts = Counter(
        obs.get('district') for obs in observations if obs.get('district')
    )
    rows = []
    row_types = []
    for district, count in sorted(district_counts.items(), key=lambda item: item[1], reverse=True):
        # Share column disabled for all report tables.
        # district_share = round(count / sum(district_counts.values()) * 100, 1)
        block_counts = Counter(
            obs.get('block')
            for obs in observations
            if obs.get('district') == district and obs.get('block')
        )
        if block_counts:
            for block, block_count in block_counts.most_common():
                # Share column disabled for all report tables.
                # block_share = round(block_count / count * 100, 1)
                # rows.append((f'{district} - {block}', block_count, block_share))
                rows.append((f'{district} - {block}', block_count))
                row_types.append('detail')
        # rows.append((district, count, district_share))  # Share column disabled
        rows.append((district, count))
        row_types.append('total')
    return rows, row_types


def generate_charts_for_sightings(observations, output_folder):
    """Generate all charts for sightings and return list of file paths with summary data."""
    chart_files = []
    summary_data = []

    if not observations:
        raise ValueError("No observations provided")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)

    total_sightings = len(observations)

    # 1. Monthly frequency of sightings
    try:
        monthly_counts = Counter()
        for obs in observations:
            submitted_at = _get_obs_field(obs, 'submitted_at', 'submittedAt')
            if submitted_at:
                try:
                    dt = datetime.fromisoformat(str(submitted_at).replace('Z', '+00:00'))
                    monthly_counts[dt.strftime('%Y-%m')] += 1
                except (ValueError, AttributeError):
                    continue

        if monthly_counts:
            sorted_months = sorted(monthly_counts.items())
            month_labels = []
            for month_str, _ in sorted_months:
                dt = datetime.strptime(month_str, '%Y-%m')
                month_labels.append(dt.strftime('%B %Y'))
            counts = [item[1] for item in sorted_months]

            fig, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(month_labels, counts, width=0.6, color=PALETTE[0])
            ax.set_xlabel('Month', fontsize=10, labelpad=10)
            ax.set_ylabel('Number of Sightings', fontsize=10, labelpad=10)
            ax.set_title('Monthly Sightings Frequency', fontsize=13, fontweight='bold', pad=15)
            _style_chart(ax, fig)
            _add_value_labels(ax, bars)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            chart_path = os.path.join(output_folder, 'chart_monthly_frequency.png')
            _save_figure(fig, chart_path)
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Monthly Sightings Frequency',
                _share_rows(sorted_months),
            )
    except Exception as e:
        plt.close('all')
        print(f"Error generating monthly frequency chart: {str(e)}")

    # 2. Geography - overall district share
    district_counts = Counter(
        obs.get('district') for obs in observations if obs.get('district')
    )
    if district_counts:
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_geography_overall.png',
            'Overall Geography - District Share of Sightings',
            district_counts,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Overall Geography - District Share of Sightings',
                rows,
                # Share column disabled for this section.
                # columns=['District', 'Count', 'Share'],
                columns=['District', 'Count'],
            )

        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_districts.png',
            'District Sightings Distribution',
            district_counts,
            'District',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'District Sightings Distribution',
                rows,
                # Share column disabled for this section.
                # columns=['District', 'Count', 'Share'],
                columns=['District', 'Count'],
            )

        district_rows, district_row_types = _district_breakdown_rows(observations)
        if chart_path and district_rows:
            summary_data[-1]['extra_tables'] = [{
                'title': 'Geography by District - Block Breakdown',
                # Share column disabled for this section.
                # 'columns': ['Location', 'Count', 'Share'],
                'columns': ['Location', 'Count'],
                'data': district_rows,
                'row_types': district_row_types,
            }]

    # 3. Block sightings distribution
    block_counts = Counter(obs.get('block') for obs in observations if obs.get('block'))
    if block_counts:
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_blocks.png',
            'Block Sightings Distribution',
            block_counts,
            'Block',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Block Sightings Distribution',
                rows,
                # Share column disabled for this section.
                # columns=['Block', 'Count', 'Share'],
                columns=['Block', 'Count'],
            )

    # 4. Site, ghat, and village sightings distribution
    location_counts = _collect_location_counts(observations)
    if location_counts:
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_locations.png',
            'Site, Ghat and Village Sightings Distribution',
            location_counts,
            'Location',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Site, Ghat and Village Sightings Distribution',
                rows,
                # Share column disabled for this section.
                # columns=['Location', 'Count', 'Share'],
                columns=['Location', 'Count'],
            )

        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_locations_pie.png',
            'Site, Ghat and Village Share of Sightings',
            location_counts,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Site, Ghat and Village Share of Sightings',
                rows,
                # Share column disabled for this section.
                # columns=['Location', 'Count', 'Share'],
                columns=['Location', 'Count'],
            )

    # 5. Species sightings share (overall)
    species_totals, species_age = _collect_species_metrics(observations)
    if species_totals:
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_species_overall_pie.png',
            'Species Share of Animal Sightings',
            species_totals,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Species Share of Animal Sightings',
                rows,
            )

        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_species_overall.png',
            'Species Sightings Distribution',
            species_totals,
            'Species',
            ylabel='Number of Animals',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Species Sightings Distribution',
                rows,
            )

    # 6. Species age composition
    if species_age:
        chart_path, rows = _create_stacked_bar_chart(
            output_folder,
            'chart_species_age.png',
            'Species Age Composition',
            species_age,
            'Species',
            stack_order=AGE_GROUP_KEYS,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Species Age Composition',
                rows,
            )

        age_summary_rows = []
        for species_type, age_counter in sorted(
            species_age.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        ):
            # total used only by disabled Share calculation below.
            # total = sum(age_counter.values())
            for age_group in AGE_GROUP_KEYS:
                count = age_counter.get(age_group, 0)
                if count:
                    # Share column disabled for this section.
                    # age_summary_rows.append(
                    #     (f'{_format_label(species_type)} - {age_group}', count, round(count / total * 100, 1))
                    # )
                    age_summary_rows.append(
                        (f'{_format_label(species_type)} - {age_group}', count)
                    )

        if chart_path and age_summary_rows:
            summary_data[-1]['extra_tables'] = [{
                'title': 'Species Age Composition - Detailed Share',
                # Share column disabled for this section.
                # 'columns': ['Species and Age Group', 'Count', 'Share'],
                'columns': ['Species and Age Group', 'Count'],
                'data': age_summary_rows,
            }]

    # 7. Species sightings by river flow
    species_by_flow = _collect_species_by_dimension(
        observations,
        ('waterBodyConditions', 'waterBodyCondition'),
        fallback_label='Not Recorded',
    )
    if species_by_flow and any(species_by_flow.values()):
        chart_path, rows = _create_stacked_bar_chart(
            output_folder,
            'chart_species_flow.png',
            'Species Sightings by River Flow',
            species_by_flow,
            'River Flow',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Species Sightings by River Flow',
                rows,
            )

        flow_totals = Counter({flow: sum(counter.values()) for flow, counter in species_by_flow.items()})
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_flow_pie.png',
            'River Flow Share of Species Sightings',
            flow_totals,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'River Flow Share of Species Sightings',
                rows,
            )

    # 8. Species sightings by weather condition
    species_by_weather = _collect_species_by_dimension(
        observations,
        ('weatherCondition', 'weather', 'weatherConditions'),
    )
    if species_by_weather and any(species_by_weather.values()):
        chart_path, rows = _create_stacked_bar_chart(
            output_folder,
            'chart_species_weather.png',
            'Species Sightings by Weather Condition',
            species_by_weather,
            'Weather Condition',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Species Sightings by Weather Condition',
                rows,
            )

        weather_totals = Counter(
            {weather: sum(counter.values()) for weather, counter in species_by_weather.items()}
        )
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_weather_pie.png',
            'Weather Condition Share of Sightings',
            weather_totals,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Weather Condition Share of Sightings',
                rows,
            )

    # 9. Species sightings by river channel type
    species_by_channel = _collect_species_by_dimension(
        observations,
        ('riverChannel', 'riverChannelType', 'channelType', 'waterBody'),
    )
    if species_by_channel and any(species_by_channel.values()):
        chart_path, rows = _create_stacked_bar_chart(
            output_folder,
            'chart_species_channel.png',
            'Species Sightings by River Channel Type',
            species_by_channel,
            'River Channel Type',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Species Sightings by River Channel Type',
                rows,
            )

        channel_totals = Counter(
            {channel: sum(counter.values()) for channel, counter in species_by_channel.items()}
        )
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_channel_pie.png',
            'River Channel Type Share of Sightings',
            channel_totals,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'River Channel Type Share of Sightings',
                rows,
            )

    # 10. Disturbance share (overall)
    disturbance_counts = _collect_disturbance_counts(observations)
    if disturbance_counts:
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_disturbance_pie.png',
            'Overall Disturbance Share',
            disturbance_counts,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Overall Disturbance Share',
                rows,
            )

        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_disturbance.png',
            'Disturbance Type Distribution',
            disturbance_counts,
            'Disturbance Type',
            ylabel='Frequency',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Disturbance Type Distribution',
                rows,
            )

    # 11. Fishing gear type share
    gear_counts = _collect_fishing_gear_counts(observations)
    if gear_counts:
        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_fishing_gear_pie.png',
            'Fishing Gear Type Share',
            gear_counts,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Fishing Gear Type Share',
                rows,
            )

        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_fishing_gear.png',
            'Fishing Gear Type Distribution',
            gear_counts,
            'Gear Type',
            ylabel='Frequency',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Fishing Gear Type Distribution',
                rows,
            )

    # 12. Legacy aggregate age group distribution (overall)
    age_groups = Counter()
    for obs in observations:
        for sp in obs.get('species', []):
            for age_group, count in _species_age_counts(sp).items():
                age_groups[age_group] += count

    if any(age_groups.values()):
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_agegroups.png',
            'Overall Age Group Distribution',
            age_groups,
            'Age Group',
            ylabel='Number of Animals',
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Overall Age Group Distribution',
                rows,
            )

        chart_path, rows = _create_pie_chart(
            output_folder,
            'chart_agegroups_pie.png',
            'Overall Age Group Share',
            age_groups,
        )
        if chart_path:
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Overall Age Group Share',
                rows,
            )

    if not chart_files and total_sightings:
        raise ValueError('No charts generated. Please check your data contains valid fields')

    return chart_files, summary_data


def generate_charts_for_reportings(observations, output_folder):
    """Generate all charts for reportings and return list of file paths with summary data."""
    chart_files = []
    summary_data = []

    if not observations:
        raise ValueError("No observations provided")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)

    # 1. Monthly frequency of reportings
    try:
        monthly_counts = Counter()
        for obs in observations:
            submitted_at = _get_obs_field(obs, 'submitted_at', 'submittedAt')
            if submitted_at:
                try:
                    dt = datetime.fromisoformat(str(submitted_at).replace('Z', '+00:00'))
                    monthly_counts[dt.strftime('%Y-%m')] += 1
                except (ValueError, AttributeError):
                    continue

        if monthly_counts:
            sorted_months = sorted(monthly_counts.items())
            month_labels = []
            for month_str, _ in sorted_months:
                dt = datetime.strptime(month_str, '%Y-%m')
                month_labels.append(dt.strftime('%B %Y'))
            counts = [item[1] for item in sorted_months]

            fig, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(month_labels, counts, width=0.6, color=PALETTE[0])
            ax.set_xlabel('Month', fontsize=10, labelpad=10)
            ax.set_ylabel('Number of Reportings', fontsize=10, labelpad=10)
            ax.set_title('Monthly Reportings Frequency', fontsize=13, fontweight='bold', pad=15)
            _style_chart(ax, fig)
            _add_value_labels(ax, bars)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            chart_path = os.path.join(output_folder, 'chart_monthly_frequency.png')
            _save_figure(fig, chart_path)
            _append_summary(
                chart_files,
                summary_data,
                chart_path,
                'Monthly Frequency Summary',
                _share_rows(sorted_months),
            )
    except Exception as e:
        plt.close('all')
        print(f"Error generating monthly frequency chart: {str(e)}")

    # 2. Frequency of reportings by block
    try:
        block_counts = Counter(obs.get('block') for obs in observations if obs.get('block'))
        if block_counts:
            chart_path, rows = _create_bar_chart(
                output_folder,
                'chart_blocks.png',
                'Reportings by Block',
                block_counts,
                'Block',
                ylabel='Number of Reportings',
            )
            if chart_path:
                _append_summary(chart_files, summary_data, chart_path, 'Block Summary', rows)
    except Exception as e:
        plt.close('all')
        print(f"Error generating block chart: {str(e)}")

    # 3. Frequency of reportings by district
    district_counts = Counter(obs.get('district') for obs in observations if obs.get('district'))
    if district_counts:
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_districts.png',
            'Reportings by District',
            district_counts,
            'District',
            ylabel='Number of Reportings',
        )
        if chart_path:
            _append_summary(chart_files, summary_data, chart_path, 'District Summary', rows)

    # 4. Species distribution
    species_counts = Counter()
    for obs in observations:
        species_list = obs.get('species', [])
        for sp in species_list:
            species_type = sp.get('type', 'Unknown')
            species_counts[species_type] += 1

    if species_counts:
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_species.png',
            'Reportings by Species',
            species_counts,
            'Species',
            ylabel='Number of Reportings',
        )
        if chart_path:
            _append_summary(chart_files, summary_data, chart_path, 'Species Summary', rows)

    # 5. Status distribution (stranded, injured, dead)
    status_counts = {'Stranded': 0, 'Injured': 0, 'Dead': 0}
    for obs in observations:
        species_list = obs.get('species', [])
        for sp in species_list:
            for age_group in ['adult', 'adultMale', 'adultFemale', 'subAdult']:
                age_data = sp.get(age_group, {})
                if isinstance(age_data, dict):
                    status_counts['Stranded'] += age_data.get('stranded', 0)
                    status_counts['Injured'] += age_data.get('injured', 0)
                    status_counts['Dead'] += age_data.get('dead', 0)

    if any(status_counts.values()):
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_status.png',
            'Animals by Status',
            status_counts,
            'Status',
            ylabel='Count',
        )
        if chart_path:
            _append_summary(chart_files, summary_data, chart_path, 'Status Summary', rows)

    # 6. Causes distribution
    all_causes = []
    for obs in observations:
        causes_list = obs.get('causes', [])
        for cause_item in causes_list:
            causes = cause_item.get('cause', [])
            if causes:
                all_causes.extend(causes)
            other_cause = cause_item.get('otherCause')
            if other_cause:
                all_causes.append(f"Other: {other_cause}")

    if all_causes:
        cause_counts = Counter(all_causes)
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_causes.png',
            'Distribution of Causes',
            cause_counts,
            'Cause',
            ylabel='Frequency',
        )
        if chart_path:
            _append_summary(chart_files, summary_data, chart_path, 'Causes Summary', rows)

    # 7. Age group distribution
    age_groups = {'Adult': 0, 'Adult Male': 0, 'Adult Female': 0, 'Sub-Adult': 0}
    for obs in observations:
        species_list = obs.get('species', [])
        for sp in species_list:
            adult_data = sp.get('adult', {})
            if isinstance(adult_data, dict):
                age_groups['Adult'] += (
                    adult_data.get('stranded', 0)
                    + adult_data.get('injured', 0)
                    + adult_data.get('dead', 0)
                )

            adult_male_data = sp.get('adultMale', {})
            if isinstance(adult_male_data, dict):
                age_groups['Adult Male'] += (
                    adult_male_data.get('stranded', 0)
                    + adult_male_data.get('injured', 0)
                    + adult_male_data.get('dead', 0)
                )

            adult_female_data = sp.get('adultFemale', {})
            if isinstance(adult_female_data, dict):
                age_groups['Adult Female'] += (
                    adult_female_data.get('stranded', 0)
                    + adult_female_data.get('injured', 0)
                    + adult_female_data.get('dead', 0)
                )

            sub_adult_data = sp.get('subAdult', {})
            if isinstance(sub_adult_data, dict):
                age_groups['Sub-Adult'] += (
                    sub_adult_data.get('stranded', 0)
                    + sub_adult_data.get('injured', 0)
                    + sub_adult_data.get('dead', 0)
                )

    if any(age_groups.values()):
        chart_path, rows = _create_bar_chart(
            output_folder,
            'chart_agegroups.png',
            'Age Group Distribution',
            age_groups,
            'Age Group',
            ylabel='Count',
        )
        if chart_path:
            _append_summary(chart_files, summary_data, chart_path, 'Age Group Summary', rows)

    return chart_files, summary_data


# Backwards compatibility - defaults to sightings
def generate_charts(observations, output_folder):
    """Generate charts - defaults to sightings for backwards compatibility."""
    return generate_charts_for_sightings(observations, output_folder)
