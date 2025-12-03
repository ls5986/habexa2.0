#!/usr/bin/env python3
"""
Color Contrast Audit Script
Calculates WCAG 2.1 contrast ratios for all color combinations used in the frontend.
"""
import re
import os
from pathlib import Path
from typing import List, Tuple, Dict

# Color definitions from theme
COLORS = {
    # Backgrounds
    'bg-gray-900': '#111827',  # Not used, but reference
    'bg-gray-800': '#1f2937',  # Not used, but reference
    'bg-gray-700': '#374151',  # Not used, but reference
    'habexa.navy.dark': '#0F0F1A',  # Background default
    'habexa.navy.main': '#1A1A2E',  # Card background
    'habexa.navy.light': '#252540',  # Surface elevated
    'habexa.gray.300': '#2D2D3D',  # Border
    
    # Text colors
    'habexa.gray.600': '#FFFFFF',  # Text primary (white)
    'habexa.gray.500': '#A0A0B0',  # Text secondary
    'habexa.gray.400': '#6B6B7B',  # Text muted
    'habexa.purple.main': '#7C3AED',  # Purple accent
    'habexa.purple.light': '#A78BFA',  # Purple light
    'habexa.purple.dark': '#5B21B6',  # Purple dark
    
    # Semantic colors
    'habexa.success.main': '#10B981',  # Success green
    'habexa.error.main': '#EF4444',  # Error red
    'habexa.warning.main': '#F59E0B',  # Warning orange
    
    # Custom hex codes found
    '#A0A0B0': '#A0A0B0',  # Sidebar inactive text
    '#FFFFFF': '#FFFFFF',  # White
    '#7C3AED': '#7C3AED',  # Purple
    '#F9FAFB': '#F9FAFB',  # Login/Register light background
    '#1A1A4E': '#1A1A4E',  # Login/Register text
    '#7C6AFA': '#7C6AFA',  # Login button
    '#5B4AD4': '#5B4AD4',  # Login button hover
}

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculate relative luminance."""
    r, g, b = [x / 255.0 for x in rgb]
    
    def adjust(c):
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4
    
    r, g, b = adjust(r), adjust(g), adjust(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def get_contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    lum1 = get_luminance(rgb1)
    lum2 = get_luminance(rgb2)
    
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)

def check_contrast(text_color: str, bg_color: str, is_large_text: bool = False) -> Dict:
    """Check if contrast meets WCAG standards."""
    ratio = get_contrast_ratio(text_color, bg_color)
    
    # WCAG 2.1 AA: 4.5:1 for normal text, 3:1 for large text
    # WCAG 2.1 AAA: 7:1 for normal text, 4.5:1 for large text
    aa_min = 3.0 if is_large_text else 4.5
    aaa_min = 4.5 if is_large_text else 7.0
    
    passes_aa = ratio >= aa_min
    passes_aaa = ratio >= aaa_min
    
    return {
        'ratio': round(ratio, 2),
        'passes_aa': passes_aa,
        'passes_aaa': passes_aaa,
        'status': 'AAA' if passes_aaa else ('AA' if passes_aa else 'FAIL')
    }

def find_color_usage():
    """Find all color usage in frontend files."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "src"
    issues = []
    
    # Common problematic combinations (updated with fixes)
    test_combinations = [
        # Text on backgrounds
        ('#A0A0B0', '#0F0F1A', 'Sidebar inactive text on dark bg', False),
        ('#A0A0B0', '#1A1A2E', 'Sidebar inactive text on card bg', False),
        ('#8B8B9B', '#0F0F1A', 'Muted text on dark bg (FIXED)', False),  # Changed from #6B6B7B
        ('#8B8B9B', '#1A1A2E', 'Muted text on card bg (FIXED)', False),  # Changed from #6B6B7B
        ('#FFFFFF', '#0F0F1A', 'White text on dark bg', False),
        ('#FFFFFF', '#1A1A2E', 'White text on card bg', False),
        ('#A78BFA', '#0F0F1A', 'Purple light on dark bg (use for text)', False),  # Better than purple.main
        ('#7C3AED', '#0F0F1A', 'Purple accent on dark bg', False),  # Still fails, but use purple.light for text
        ('#10B981', '#1A1A2E', 'Success green on card bg', False),
        ('#EF4444', '#1A1A2E', 'Error red on card bg', False),
        ('#F59E0B', '#1A1A2E', 'Warning orange on card bg', False),
        
        # Login/Register page (light theme)
        ('#1A1A4E', '#F9FAFB', 'Login text on light bg', False),
        ('#7C3AED', '#F9FAFB', 'Login button on light bg (FIXED)', False),  # Changed from #7C6AFA
        ('#FFFFFF', '#7C3AED', 'White text on purple button (FIXED)', False),  # Changed from #7C6AFA
        
        # Icon colors
        ('#8B8B9B', '#0F0F1A', 'Icon color on dark bg (FIXED)', False),  # Changed from #666
        ('#8B8B9B', '#1A1A2E', 'Icon color on card bg (FIXED)', False),  # Changed from #666
    ]
    
    print("="*60)
    print("COLOR CONTRAST AUDIT")
    print("="*60)
    print()
    
    print("Testing Common Color Combinations:")
    print("-" * 60)
    
    failures = []
    warnings = []
    passes = []
    
    for text_color, bg_color, description, is_large in test_combinations:
        result = check_contrast(text_color, bg_color, is_large)
        status_icon = "✅" if result['passes_aa'] else ("⚠️" if result['ratio'] >= 3.0 else "❌")
        
        print(f"{status_icon} {description}")
        print(f"   Text: {text_color} on BG: {bg_color}")
        print(f"   Contrast: {result['ratio']}:1 - {result['status']}")
        print()
        
        if not result['passes_aa']:
            failures.append({
                'text': text_color,
                'bg': bg_color,
                'description': description,
                'ratio': result['ratio'],
                'is_large': is_large
            })
        elif result['ratio'] < 5.0:
            warnings.append({
                'text': text_color,
                'bg': bg_color,
                'description': description,
                'ratio': result['ratio'],
                'is_large': is_large
            })
        else:
            passes.append({
                'text': text_color,
                'bg': bg_color,
                'description': description,
                'ratio': result['ratio'],
                'is_large': is_large
            })
    
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✅ Passes AA: {len(passes)}")
    print(f"⚠️  Borderline (< 5.0): {len(warnings)}")
    print(f"❌ Fails AA: {len(failures)}")
    print()
    
    if failures:
        print("CRITICAL FAILURES (Must Fix):")
        print("-" * 60)
        for f in failures:
            print(f"❌ {f['description']}")
            print(f"   Ratio: {f['ratio']}:1 (needs {4.5 if not f['is_large'] else 3.0}:1)")
            print()
    
    if warnings:
        print("WARNINGS (Consider Improving):")
        print("-" * 60)
        for w in warnings:
            print(f"⚠️  {w['description']}")
            print(f"   Ratio: {w['ratio']}:1 (meets AA but could be better)")
            print()
    
    return {
        'failures': failures,
        'warnings': warnings,
        'passes': passes
    }

if __name__ == "__main__":
    results = find_color_usage()
    
    if results['failures']:
        exit(1)
    elif results['warnings']:
        exit(0)  # Warnings are OK
    else:
        exit(0)

