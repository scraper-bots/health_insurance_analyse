import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
import sys
import warnings

warnings.filterwarnings('ignore')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Set clean style
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.figsize': (10, 6)
})

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data')
CHARTS_DIR = os.path.join(ROOT_DIR, 'charts')

os.makedirs(CHARTS_DIR, exist_ok=True)

# Clear old charts
for f in os.listdir(CHARTS_DIR):
    if f.endswith('.png'):
        os.remove(os.path.join(CHARTS_DIR, f))

# Load data
df = pd.read_csv(os.path.join(DATA_DIR, 'combined.csv'))
print(f"Loaded {len(df)} records")
print("Generating 8 unique charts...")

# Define consistent colors
COMPANY_COLORS = {
    'Pasha Insurance': '#E53935',
    'A-Group': '#8E24AA',
    'Ateshgah': '#43A047',
    'AIIC': '#1E88E5',
    'Meqa Sigorta': '#FB8C00'
}
TYPE_COLORS = {
    'CLINIC': '#1E88E5',
    'PHARMACY': '#43A047',
    'DENTAL': '#E53935',
    'OPTICS': '#8E24AA'
}

# ============================================================
# CHART 1: Network Size by Insurance Company
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5))
source_counts = df['source'].value_counts().sort_values()
colors = [COMPANY_COLORS[s] for s in source_counts.index]
bars = ax.barh(source_counts.index, source_counts.values, color=colors, height=0.6)
for bar in bars:
    width = bar.get_width()
    ax.text(width + 8, bar.get_y() + bar.get_height()/2, f'{int(width)}',
            va='center', fontsize=12, fontweight='bold')
ax.set_xlabel('Number of Healthcare Providers')
ax.set_title('Provider Network Size by Insurance Company', fontweight='bold', pad=15)
ax.set_xlim(0, source_counts.max() * 1.18)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '01_network_size.png'), dpi=150, facecolor='white')
plt.close()
print("  1/8: 01_network_size.png")

# ============================================================
# CHART 2: Provider Type Breakdown (Donut Chart)
# ============================================================
fig, ax = plt.subplots(figsize=(9, 7))
type_counts = df['type'].value_counts()
colors = [TYPE_COLORS[t] for t in type_counts.index]
wedges, texts, autotexts = ax.pie(
    type_counts.values,
    colors=colors,
    autopct='%1.1f%%',
    pctdistance=0.75,
    startangle=90,
    wedgeprops={'width': 0.5, 'edgecolor': 'white', 'linewidth': 2}
)
for autotext in autotexts:
    autotext.set_fontsize(12)
    autotext.set_fontweight('bold')
    autotext.set_color('white')

# Add center text
ax.text(0, 0, f'{len(df):,}\nTotal', ha='center', va='center', fontsize=16, fontweight='bold')

# Custom legend
legend_labels = [f'{t} ({c})' for t, c in zip(type_counts.index, type_counts.values)]
ax.legend(wedges, legend_labels, title='Provider Type', loc='center left',
          bbox_to_anchor=(0.95, 0.5), fontsize=11)
ax.set_title('Healthcare Provider Types Distribution', fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '02_provider_types.png'), dpi=150, facecolor='white')
plt.close()
print("  2/8: 02_provider_types.png")

# ============================================================
# CHART 3: Geographic Concentration (Baku vs Regions)
# ============================================================
fig, ax = plt.subplots(figsize=(8, 6))
baku_count = len(df[df['region_category'] == 'Bakı'])
region_count = len(df[df['region_category'] == 'Region'])
total = baku_count + region_count

categories = ['Baku\nMetropolitan', 'Regional\nAreas']
values = [baku_count, region_count]
percentages = [baku_count/total*100, region_count/total*100]
colors = ['#E53935', '#1E88E5']

bars = ax.bar(categories, values, color=colors, width=0.5, edgecolor='white', linewidth=2)
for bar, val, pct in zip(bars, values, percentages):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
            f'{val}\n({pct:.0f}%)', ha='center', va='bottom', fontsize=14, fontweight='bold')

ax.set_ylabel('Number of Providers')
ax.set_title('Geographic Concentration of Healthcare Providers', fontweight='bold', pad=15)
ax.set_ylim(0, max(values) * 1.25)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '03_geographic_concentration.png'), dpi=150, facecolor='white')
plt.close()
print("  3/8: 03_geographic_concentration.png")

# ============================================================
# CHART 4: Company Strategy Heatmap (Type x Company)
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))
pivot = df.groupby(['source', 'type']).size().unstack(fill_value=0)
pivot = pivot.reindex(columns=['PHARMACY', 'CLINIC', 'DENTAL', 'OPTICS'])
pivot = pivot.loc[df['source'].value_counts().index]  # Sort by total size

# Create heatmap
im = ax.imshow(pivot.values, cmap='YlGnBu', aspect='auto')

# Add text annotations
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        val = pivot.values[i, j]
        color = 'white' if val > pivot.values.max() * 0.5 else 'black'
        ax.text(j, i, f'{val}', ha='center', va='center', fontsize=12, fontweight='bold', color=color)

ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns, fontsize=11)
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index, fontsize=11)
ax.set_title('Provider Type Distribution by Insurance Company', fontweight='bold', pad=15)

# Colorbar
cbar = plt.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label('Number of Providers', fontsize=11)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '04_company_strategy_heatmap.png'), dpi=150, facecolor='white')
plt.close()
print("  4/8: 04_company_strategy_heatmap.png")

# ============================================================
# CHART 5: Regional Coverage Comparison
# ============================================================
fig, ax = plt.subplots(figsize=(11, 6))

pivot_region = df.groupby(['source', 'region_category']).size().unstack(fill_value=0)
pivot_region = pivot_region.reindex(columns=['Bakı', 'Region'])
companies = pivot_region.index.tolist()

x = np.arange(len(companies))
width = 0.35

bars1 = ax.bar(x - width/2, pivot_region['Bakı'], width, label='Baku', color='#E53935', edgecolor='white')
bars2 = ax.bar(x + width/2, pivot_region['Region'], width, label='Regions', color='#1E88E5', edgecolor='white')

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2, height + 3, f'{int(height)}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.set_ylabel('Number of Providers')
ax.set_title('Insurance Company Coverage: Baku vs Regional Areas', fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(companies, rotation=0, ha='center', fontsize=10)
ax.legend(loc='upper right', fontsize=11)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, pivot_region.values.max() * 1.15)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '05_regional_coverage.png'), dpi=150, facecolor='white')
plt.close()
print("  5/8: 05_regional_coverage.png")

# ============================================================
# CHART 6: Top Cities Outside Baku
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

# Get cities excluding Baku
city_counts = df[df['region_category'] == 'Region']['city'].value_counts().head(12)
colors = plt.cm.viridis(np.linspace(0.3, 0.85, len(city_counts)))

bars = ax.barh(range(len(city_counts)), city_counts.values, color=colors, height=0.7)
ax.set_yticks(range(len(city_counts)))
ax.set_yticklabels(city_counts.index, fontsize=11)
ax.invert_yaxis()

for bar in bars:
    width = bar.get_width()
    ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{int(width)}',
            va='center', fontsize=11, fontweight='bold')

ax.set_xlabel('Number of Healthcare Providers')
ax.set_title('Top Regional Cities by Healthcare Provider Count', fontweight='bold', pad=15)
ax.set_xlim(0, city_counts.max() * 1.15)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '06_top_regional_cities.png'), dpi=150, facecolor='white')
plt.close()
print("  6/8: 06_top_regional_cities.png")

# ============================================================
# CHART 7: Specialty Services Gap (Dental + Optics)
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

specialty_data = []
for source in df['source'].unique():
    source_df = df[df['source'] == source]
    dental = len(source_df[source_df['type'] == 'DENTAL'])
    optics = len(source_df[source_df['type'] == 'OPTICS'])
    specialty_data.append({'source': source, 'Dental': dental, 'Optics': optics})

spec_df = pd.DataFrame(specialty_data)
spec_df = spec_df.sort_values(by=['Dental', 'Optics'], ascending=False)

x = np.arange(len(spec_df))
width = 0.35

bars1 = ax.bar(x - width/2, spec_df['Dental'], width, label='Dental Clinics', color='#E53935', edgecolor='white')
bars2 = ax.bar(x + width/2, spec_df['Optics'], width, label='Optical Stores', color='#8E24AA', edgecolor='white')

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2, height + 0.3, f'{int(height)}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.set_ylabel('Number of Providers')
ax.set_title('Specialty Care Networks: Dental & Optical Coverage', fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(spec_df['source'], rotation=0, ha='center', fontsize=10)
ax.legend(loc='upper right', fontsize=11)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '07_specialty_services.png'), dpi=150, facecolor='white')
plt.close()
print("  7/8: 07_specialty_services.png")

# ============================================================
# CHART 8: Azerbaijan Geographic Distribution
# ============================================================
fig, ax = plt.subplots(figsize=(12, 9))

geo_df = df[(df['latitude'].notna()) & (df['longitude'].notna())]
geo_df = geo_df[(geo_df['latitude'] >= 38.5) & (geo_df['latitude'] <= 42) &
                (geo_df['longitude'] >= 44.5) & (geo_df['longitude'] <= 51)]

for source in ['Pasha Insurance', 'A-Group', 'Ateshgah', 'AIIC', 'Meqa Sigorta']:
    subset = geo_df[geo_df['source'] == source]
    if len(subset) > 0:
        ax.scatter(subset['longitude'], subset['latitude'],
                   c=COMPANY_COLORS[source], label=f'{source} ({len(subset)})',
                   alpha=0.6, s=35, edgecolors='white', linewidth=0.5)

ax.set_xlabel('Longitude', fontsize=12)
ax.set_ylabel('Latitude', fontsize=12)
ax.set_title('Healthcare Provider Distribution Across Azerbaijan', fontweight='bold', pad=15)
ax.legend(title='Insurance Company', loc='upper left', fontsize=10, title_fontsize=11,
          framealpha=0.9, edgecolor='gray')
ax.set_facecolor('#f8f9fa')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '08_azerbaijan_map.png'), dpi=150, facecolor='white')
plt.close()
print("  8/8: 08_azerbaijan_map.png")

print("\n" + "=" * 50)
print("All 8 charts generated successfully!")
print(f"Charts saved to: {CHARTS_DIR}")
print("=" * 50)
