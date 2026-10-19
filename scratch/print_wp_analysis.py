import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.stdout = open('scratch/wp_analysis.txt', 'w', encoding='utf-8')

data = json.loads(open('scratch/wp_comparison.json', encoding='utf-8').read())

print("="*80)
print("1. CHI TIẾT 9 CA PROSECUTOR ĐOÁN ĐÚNG APPEAL TO WORSE PROBLEMS (GOLD WP)")
print("="*80)

for i, d in enumerate(data['wp_true'], 1):
    print(f"\n[Ca ĐÚNG {i:02d}] ID: {d['sample_id']} | Gold: {d['gold']}")
    print(f"Target Comment:\n  \"{d['comment']}\"")
    if d['parent_comment']:
        print(f"Parent Comment:\n  \"{d['parent_comment']}\"")
    print(f"Prosecutor Quote:\n  \"{d['pros_quote']}\"")
    print(f"Prosecutor Defect:\n  {d['pros_defect']}")
    print(f"Prosecutor Runner-up: {d['pros_ru']} (Quote: \"{d['pros_ru_quote']}\")")

print("\n" + "="*80)
print("2. CHI TIẾT 14 CA PROSECUTOR ĐOÁN SAI APPEAL TO WORSE PROBLEMS (GOLD KHÔNG PHẢI WP)")
print("="*80)

for i, d in enumerate(data['wp_false'], 1):
    print(f"\n[Ca SAI {i:02d}] ID: {d['sample_id']} | Gold: {d['gold']}")
    print(f"Target Comment:\n  \"{d['comment']}\"")
    if d['parent_comment']:
        print(f"Parent Comment:\n  \"{d['parent_comment']}\"")
    print(f"Prosecutor Quote:\n  \"{d['pros_quote']}\"")
    print(f"Prosecutor Defect:\n  {d['pros_defect']}")
    print(f"Prosecutor Runner-up: {d['pros_ru']} (Quote: \"{d['pros_ru_quote']}\")")
