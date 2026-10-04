#!/usr/bin/env python3
"""
Data Extraction Flowchart for Scoping Review Protocol
生成数据提取流程图
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# Set up Chinese font support
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(1, 1, figsize=(12, 10))
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
ax.axis('off')

def draw_box(ax, x, y, width, height, text, color='#E8F4FD', edge_color='#2E86AB'):
    """Draw a rounded rectangle box with text"""
    box = FancyBboxPatch((x - width/2, y - height/2), width, height,
                         boxstyle="round,pad=0.05,rounding_size=0.2",
                         facecolor=color, edgecolor=edge_color, linewidth=2)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=10,
            fontweight='bold', wrap=True)

def draw_diamond(ax, x, y, size, text, color='#FFF3CD', edge_color='#F0AD4E'):
    """Draw a diamond shape for decision points"""
    diamond = plt.Polygon([(x, y+size), (x+size, y), (x, y-size), (x-size, y)],
                          facecolor=color, edgecolor=edge_color, linewidth=2)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold')

def draw_arrow(ax, start, end, color='#333333'):
    """Draw an arrow between two points"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

# Title
ax.text(6, 9.5, '数据提取流程图\nData Extraction Flowchart',
        ha='center', va='center', fontsize=14, fontweight='bold')

# Step 1: Start - Literature Pool
draw_box(ax, 6, 8.5, 3, 0.6, '纳入文献库\nIncluded Studies', '#D4EDDA', '#28A745')

# Step 2: Parallel extraction
draw_box(ax, 3, 7.2, 2.8, 0.8, 'Reviewer A\n独立提取', '#E8F4FD', '#2E86AB')
draw_box(ax, 9, 7.2, 2.8, 0.8, 'Reviewer B\n独立提取', '#E8F4FD', '#2E86AB')

# Arrows from start to parallel
draw_arrow(ax, (5, 8.2), (3.5, 7.6))
draw_arrow(ax, (7, 8.2), (8.5, 7.6))

# Step 3: Data comparison
draw_box(ax, 6, 5.8, 3.2, 0.7, '数据比对\nData Comparison', '#E8F4FD', '#2E86AB')

# Arrows to comparison
draw_arrow(ax, (3.5, 6.8), (5, 6.15))
draw_arrow(ax, (8.5, 6.8), (7, 6.15))

# Step 4: Decision - Discrepancy?
draw_diamond(ax, 6, 4.5, 0.6, '存在\n差异?', '#FFF3CD', '#F0AD4E')

# Arrow to decision
draw_arrow(ax, (6, 5.45), (6, 5.1))

# Step 5a: No discrepancy - direct to final
draw_box(ax, 9.5, 4.5, 2, 0.6, '数据一致\nConsistent', '#D4EDDA', '#28A745')
draw_arrow(ax, (6.6, 4.5), (8.5, 4.5))
ax.text(7.5, 4.7, '否', fontsize=9, ha='center')

# Step 5b: Yes - Discussion
draw_box(ax, 6, 3.2, 3, 0.7, '讨论协商\nDiscussion', '#FCE4EC', '#E91E63')
draw_arrow(ax, (6, 3.9), (6, 3.55))
ax.text(6.2, 3.7, '是', fontsize=9, ha='left')

# Step 6: Decision - Resolved?
draw_diamond(ax, 6, 2.0, 0.55, '达成\n共识?', '#FFF3CD', '#F0AD4E')
draw_arrow(ax, (6, 2.85), (6, 2.55))

# Step 6a: Yes - to final
draw_arrow(ax, (6.55, 2.0), (8.5, 2.0))
ax.text(7.5, 2.2, '是', fontsize=9, ha='center')

# Step 6b: No - Reference original
draw_box(ax, 3, 2.0, 2.8, 0.7, '参照原文核实\nVerify with Source', '#FFF0F5', '#DC3545')
draw_arrow(ax, (5.45, 2.0), (4.4, 2.0))
ax.text(4.9, 2.2, '否', fontsize=9, ha='center')

# Arrow from reference back to resolved path
draw_arrow(ax, (3, 1.65), (3, 1.0))
draw_arrow(ax, (3, 1.0), (9.5, 1.0))

# Final step
draw_box(ax, 9.5, 2.0, 2.2, 0.6, '最终数据确认\nFinal Data', '#D4EDDA', '#28A745')

# Arrow from consistent to final
draw_arrow(ax, (9.5, 4.2), (9.5, 2.3))

# Connect all to end
draw_box(ax, 6, 0.3, 3.5, 0.5, '数据提取完成 / Extraction Complete', '#C8E6C9', '#2E7D32')
draw_arrow(ax, (9.5, 1.7), (9.5, 1.0))
draw_arrow(ax, (9.5, 1.0), (6, 1.0))
draw_arrow(ax, (6, 1.0), (6, 0.55))

plt.tight_layout()
plt.savefig('/Users/smymbp16/Desktop/Precise immunological markers/data_extraction_flowchart.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('/Users/smymbp16/Desktop/Precise immunological markers/data_extraction_flowchart.pdf',
            bbox_inches='tight', facecolor='white')
print("Flowchart saved as PNG and PDF")
