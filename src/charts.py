import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend - must be before pyplot import
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 7)  # Increased height from 6 to 7

def generate_charts_for_sightings(observations, output_folder):
    """Generate all charts for sightings and return list of file paths with summary data"""
    chart_files = []
    summary_data = []
    
    # Validate inputs
    if not observations:
        raise ValueError("No observations provided")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
    
    # 1. Frequency of sightings by block
    try:
        blocks = [obs.get('block') for obs in observations if obs.get('block')]
        if blocks:  # Only create chart if data exists
            block_counts = Counter(blocks)
            
            fig, ax = plt.subplots(figsize=(10, 7))
            bars = ax.bar(block_counts.keys(), block_counts.values(), width=0.4)
            ax.set_xlabel('Block', fontsize=12, labelpad=15)
            ax.set_ylabel('Number of Sightings', fontsize=12, labelpad=15)
            ax.set_title('Sightings by Block', fontsize=14, fontweight='bold', pad=25)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            chart_path = os.path.join(output_folder, 'chart_blocks.png')
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(chart_path)
            summary_data.append({
                'title': 'Block Summary',
                'data': sorted(block_counts.items(), key=lambda x: x[1], reverse=True)
            })
    except Exception as e:
        plt.close('all')
        print(f"Error generating block chart: {str(e)}")
    
    # 2. Frequency of sightings by district
    districts = [obs.get('district') for obs in observations if obs.get('district')]
    if districts:  # Only create chart if data exists
        district_counts = Counter(districts)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(district_counts.keys(), district_counts.values(), width=0.4, color='steelblue')
        ax.set_xlabel('District', fontsize=12, labelpad=15)
        ax.set_ylabel('Number of Sightings', fontsize=12, labelpad=15)
        ax.set_title('Sightings by District', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_districts.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'District Summary',
            'data': sorted(district_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 3. Sightings by water body type
    water_bodies = [obs.get('waterBody') for obs in observations if obs.get('waterBody')]
    if water_bodies:  # Only create chart if data exists
        water_body_counts = Counter(water_bodies)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(water_body_counts.keys(), water_body_counts.values(), width=0.4, color='teal')
        ax.set_xlabel('Water Body Type', fontsize=12, labelpad=15)
        ax.set_ylabel('Number of Sightings', fontsize=12, labelpad=15)
        ax.set_title('Sightings by Water Body Type', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_waterbodies.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Water Body Type Summary',
            'data': sorted(water_body_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 4. Sightings by weather condition
    weather = [obs.get('weatherCondition') for obs in observations if obs.get('weatherCondition')]
    if weather:  # Only create chart if data exists
        weather_counts = Counter(weather)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(weather_counts.keys(), weather_counts.values(), width=0.4, color='coral')
        ax.set_xlabel('Weather Condition', fontsize=12, labelpad=15)
        ax.set_ylabel('Number of Sightings', fontsize=12, labelpad=15)
        ax.set_title('Sightings by Weather Condition', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_weather.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Weather Condition Summary',
            'data': sorted(weather_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 5. Distribution of threats
    all_threats = []
    for obs in observations:
        threats = obs.get('threats', [])
        if threats:
            all_threats.extend(threats)
    
    if all_threats:  # Only create chart if data exists
        threat_counts = Counter(all_threats)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(threat_counts.keys(), threat_counts.values(), width=0.4, color='indianred')
        ax.set_xlabel('Threat Type', fontsize=12, labelpad=15)
        ax.set_ylabel('Frequency', fontsize=12, labelpad=15)
        ax.set_title('Distribution of Threats', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_threats.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Threats Summary',
            'data': sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 6. Age group distribution
    age_groups = {'Adult': 0, 'Sub-Adult': 0}
    for obs in observations:
        species = obs.get('species', [])
        for sp in species:
            age_groups['Adult'] += sp.get('adult', 0) + sp.get('adultMale', 0) + sp.get('adultFemale', 0)
            age_groups['Sub-Adult'] += sp.get('subAdult', 0)
    
    # Only create chart if there's data
    if age_groups['Adult'] > 0 or age_groups['Sub-Adult'] > 0:
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(age_groups.keys(), age_groups.values(), width=0.4, color='mediumseagreen')
        ax.set_xlabel('Age Group', fontsize=12, labelpad=15)
        ax.set_ylabel('Count', fontsize=12, labelpad=15)
        ax.set_title('Age Group Distribution', fontsize=14, fontweight='bold', pad=25)
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_agegroups.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Age Group Summary',
            'data': sorted(age_groups.items(), key=lambda x: x[1], reverse=True)
        })
    
    return chart_files, summary_data


def generate_charts_for_reportings(observations, output_folder):
    """Generate all charts for reportings and return list of file paths with summary data"""
    chart_files = []
    summary_data = []
    
    # Validate inputs
    if not observations:
        raise ValueError("No observations provided")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
    
    # 1. Frequency of reportings by block
    try:
        blocks = [obs.get('block') for obs in observations if obs.get('block')]
        if blocks:
            block_counts = Counter(blocks)
            
            fig, ax = plt.subplots(figsize=(10, 7))
            bars = ax.bar(block_counts.keys(), block_counts.values(), width=0.4)
            ax.set_xlabel('Block', fontsize=12, labelpad=15)
            ax.set_ylabel('Number of Reportings', fontsize=12, labelpad=15)
            ax.set_title('Reportings by Block', fontsize=14, fontweight='bold', pad=25)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            chart_path = os.path.join(output_folder, 'chart_blocks.png')
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(chart_path)
            summary_data.append({
                'title': 'Block Summary',
                'data': sorted(block_counts.items(), key=lambda x: x[1], reverse=True)
            })
    except Exception as e:
        plt.close('all')
        print(f"Error generating block chart: {str(e)}")
    
    # 2. Frequency of reportings by district
    districts = [obs.get('district') for obs in observations if obs.get('district')]
    if districts:
        district_counts = Counter(districts)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(district_counts.keys(), district_counts.values(), width=0.4, color='steelblue')
        ax.set_xlabel('District', fontsize=12, labelpad=15)
        ax.set_ylabel('Number of Reportings', fontsize=12, labelpad=15)
        ax.set_title('Reportings by District', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_districts.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'District Summary',
            'data': sorted(district_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 3. Species distribution
    species_counts = Counter()
    for obs in observations:
        species_list = obs.get('species', [])
        for sp in species_list:
            species_type = sp.get('type', 'Unknown')
            species_counts[species_type] += 1
    
    if species_counts:
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(species_counts.keys(), species_counts.values(), width=0.4, color='teal')
        ax.set_xlabel('Species', fontsize=12, labelpad=15)
        ax.set_ylabel('Number of Reportings', fontsize=12, labelpad=15)
        ax.set_title('Reportings by Species', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_species.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Species Summary',
            'data': sorted(species_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 4. Status distribution (stranded, injured, dead)
    status_counts = {'Stranded': 0, 'Injured': 0, 'Dead': 0}
    for obs in observations:
        species_list = obs.get('species', [])
        for sp in species_list:
            # Count all age groups
            for age_group in ['adult', 'adultMale', 'adultFemale', 'subAdult']:
                age_data = sp.get(age_group, {})
                if isinstance(age_data, dict):
                    status_counts['Stranded'] += age_data.get('stranded', 0)
                    status_counts['Injured'] += age_data.get('injured', 0)
                    status_counts['Dead'] += age_data.get('dead', 0)
    
    if any(status_counts.values()):
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(status_counts.keys(), status_counts.values(), width=0.4, color='coral')
        ax.set_xlabel('Status', fontsize=12, labelpad=15)
        ax.set_ylabel('Count', fontsize=12, labelpad=15)
        ax.set_title('Animals by Status', fontsize=14, fontweight='bold', pad=25)
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_status.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Status Summary',
            'data': sorted(status_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 5. Causes distribution
    all_causes = []
    for obs in observations:
        causes_list = obs.get('causes', [])
        for cause_item in causes_list:
            causes = cause_item.get('cause', [])
            if causes:
                all_causes.extend(causes)
            # Also include otherCause if present
            other_cause = cause_item.get('otherCause')
            if other_cause:
                all_causes.append(f"Other: {other_cause}")
    
    if all_causes:
        cause_counts = Counter(all_causes)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(cause_counts.keys(), cause_counts.values(), width=0.4, color='indianred')
        ax.set_xlabel('Cause', fontsize=12, labelpad=15)
        ax.set_ylabel('Frequency', fontsize=12, labelpad=15)
        ax.set_title('Distribution of Causes', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_causes.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Causes Summary',
            'data': sorted(cause_counts.items(), key=lambda x: x[1], reverse=True)
        })
    
    # 6. Age group distribution
    age_groups = {'Adult': 0, 'Adult Male': 0, 'Adult Female': 0, 'Sub-Adult': 0}
    for obs in observations:
        species_list = obs.get('species', [])
        for sp in species_list:
            adult_data = sp.get('adult', {})
            if isinstance(adult_data, dict):
                age_groups['Adult'] += adult_data.get('stranded', 0) + adult_data.get('injured', 0) + adult_data.get('dead', 0)
            
            adult_male_data = sp.get('adultMale', {})
            if isinstance(adult_male_data, dict):
                age_groups['Adult Male'] += adult_male_data.get('stranded', 0) + adult_male_data.get('injured', 0) + adult_male_data.get('dead', 0)
            
            adult_female_data = sp.get('adultFemale', {})
            if isinstance(adult_female_data, dict):
                age_groups['Adult Female'] += adult_female_data.get('stranded', 0) + adult_female_data.get('injured', 0) + adult_female_data.get('dead', 0)
            
            sub_adult_data = sp.get('subAdult', {})
            if isinstance(sub_adult_data, dict):
                age_groups['Sub-Adult'] += sub_adult_data.get('stranded', 0) + sub_adult_data.get('injured', 0) + sub_adult_data.get('dead', 0)
    
    if any(age_groups.values()):
        fig, ax = plt.subplots(figsize=(10, 7))
        bars = ax.bar(age_groups.keys(), age_groups.values(), width=0.4, color='mediumseagreen')
        ax.set_xlabel('Age Group', fontsize=12, labelpad=15)
        ax.set_ylabel('Count', fontsize=12, labelpad=15)
        ax.set_title('Age Group Distribution', fontsize=14, fontweight='bold', pad=25)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = os.path.join(output_folder, 'chart_agegroups.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_path)
        summary_data.append({
            'title': 'Age Group Summary',
            'data': sorted(age_groups.items(), key=lambda x: x[1], reverse=True)
        })
    
    return chart_files, summary_data


# Backwards compatibility - defaults to sightings
def generate_charts(observations, output_folder):
    """Generate charts - defaults to sightings for backwards compatibility"""
    return generate_charts_for_sightings(observations, output_folder)
