"""
USA Printify/Print-on-Demand Trend Finder
Discovers trending niches, themes, and product opportunities
"""

import os
import json
from datetime import datetime
import anthropic
import requests
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

class PrintifyTrendFinder:
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Google APIs
        credentials_dict = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
        creds = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        
        self.sheet_id = os.getenv("PRINTIFY_SHEET_ID", "")
        self.serper_key = os.getenv("SERPER_API_KEY")
        
        # USA demographic segments
        self.target_audiences = [
            'millennials', 'gen z', 'parents', 'dog owners', 'cat owners',
            'teachers', 'nurses', 'fitness enthusiasts', 'gamers',
            'book lovers', 'coffee lovers', 'outdoor enthusiasts'
        ]
        
        # Product types for POD
        self.product_types = [
            't-shirt', 'hoodie', 'mug', 'tote bag', 'phone case',
            'sticker', 'poster', 'canvas print', 'tank top'
        ]
    
    def find_trending_topics(self):
        """Find trending topics, memes, events in USA"""
        trends = []
        
        if not self.serper_key:
            print("  No Serper API key")
            return trends
        
        # Search queries for USA trends
        queries = [
            "trending memes USA 2025",
            "viral quotes 2025",
            "popular sayings 2025",
            "trending hobbies USA",
            "popular movements 2025",
            "trending lifestyle USA"
        ]
        
        for query in queries:
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={'X-API-KEY': self.serper_key},
                    json={'q': query, 'gl': 'us', 'num': 5},
                    timeout=10
                )
                data = response.json()
                
                for item in data.get('organic', [])[:3]:
                    trends.append({
                        'title': item.get('title'),
                        'snippet': item.get('snippet', ''),
                        'url': item.get('link')
                    })
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  Error finding trends: {e}")
        
        return trends
    
    def analyze_niche_opportunities(self, trends_data):
        """Use Claude to analyze trends and suggest POD niches"""
        
        formatted_trends = "\n\n".join([
            f"Trend: {t['title']}\n{t['snippet']}"
            for t in trends_data[:15]
        ])
        
        prompt = f"""You are a print-on-demand business consultant specializing in USA market Printify/Shopify stores.

Analyze these trending topics and themes from USA:

{formatted_trends}

Provide 10 SPECIFIC print-on-demand product opportunities. For each opportunity:

1. NICHE NAME: (specific, not generic)
2. TARGET AUDIENCE: Who buys this?
3. DESIGN THEME: What should the design look like/say?
4. PRODUCTS: Which POD products? (t-shirt, hoodie, mug, etc.)
5. DEMAND SCORE: 1-10 (how hot is this trend?)
6. COMPETITION: Low/Medium/High
7. DESIGN EXAMPLES: 3 specific text/image ideas
8. WHY IT WORKS: What makes this profitable?
9. FACEBOOK AD ANGLE: How to market this?
10. ESTIMATED MONTHLY REVENUE: Realistic estimate if executed well

Focus on:
- Specific niches (not just "dog lovers" but "golden retriever moms")
- Actionable design ideas
- USA cultural trends
- Passion-based audiences
- Gift-giving occasions
- Identity/lifestyle niches

Format each opportunity clearly with all 10 points."""

        try:
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"  Error with Claude: {e}")
            return "Analysis failed"
    
    def extract_opportunities(self, analysis_text):
        """Parse Claude's response into structured data"""
        opportunities = []
        
        # Split by numbered opportunities
        sections = analysis_text.split('\n\n')
        
        current_opp = {}
        for section in sections:
            if 'NICHE NAME:' in section or section.strip().startswith('1.') or section.strip().startswith('2.'):
                if current_opp:
                    opportunities.append(current_opp)
                    current_opp = {}
            
            # Extract fields
            if 'NICHE NAME:' in section:
                current_opp['niche'] = section.split('NICHE NAME:')[1].split('\n')[0].strip()
            elif 'TARGET AUDIENCE:' in section:
                current_opp['audience'] = section.split('TARGET AUDIENCE:')[1].split('\n')[0].strip()
            elif 'DESIGN THEME:' in section:
                current_opp['design_theme'] = section.split('DESIGN THEME:')[1].split('\n')[0].strip()
            elif 'PRODUCTS:' in section:
                current_opp['products'] = section.split('PRODUCTS:')[1].split('\n')[0].strip()
            elif 'DEMAND SCORE:' in section:
                score_text = section.split('DEMAND SCORE:')[1].split('\n')[0].strip()
                try:
                    current_opp['demand_score'] = int(score_text.split('/')[0].strip())
                except:
                    current_opp['demand_score'] = 5
            elif 'COMPETITION:' in section:
                current_opp['competition'] = section.split('COMPETITION:')[1].split('\n')[0].strip()
            elif 'DESIGN EXAMPLES:' in section:
                current_opp['design_examples'] = section.split('DESIGN EXAMPLES:')[1].split('WHY IT WORKS:')[0].strip()
            elif 'WHY IT WORKS:' in section:
                current_opp['why_works'] = section.split('WHY IT WORKS:')[1].split('FACEBOOK AD ANGLE:')[0].strip()
            elif 'FACEBOOK AD ANGLE:' in section:
                current_opp['ad_angle'] = section.split('FACEBOOK AD ANGLE:')[1].split('ESTIMATED MONTHLY REVENUE:')[0].strip()
            elif 'ESTIMATED MONTHLY REVENUE:' in section:
                current_opp['est_revenue'] = section.split('ESTIMATED MONTHLY REVENUE:')[1].strip()
        
        if current_opp:
            opportunities.append(current_opp)
        
        return opportunities
    
    def save_to_sheets(self, opportunities, raw_analysis):
        """Save opportunities to Google Sheets"""
        if not self.sheet_id or not opportunities:
            print("  No opportunities to save")
            return
        
        try:
            rows = []
            for opp in opportunities:
                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    opp.get('niche', ''),
                    opp.get('audience', ''),
                    opp.get('design_theme', ''),
                    opp.get('products', ''),
                    opp.get('demand_score', 5),
                    opp.get('competition', 'Medium'),
                    opp.get('design_examples', ''),
                    opp.get('why_works', ''),
                    opp.get('ad_angle', ''),
                    opp.get('est_revenue', ''),
                    'Not started',  # status
                    ''  # notes
                ]
                rows.append(row)
            
            body = {'values': rows}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range='Opportunities!A:M',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"\n  Saved {len(rows)} opportunities to Google Sheets")
            
            # Also save raw analysis to second sheet
            raw_row = [[
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                raw_analysis
            ]]
            
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range='Analysis!A:B',
                valueInputOption='RAW',
                body={'values': raw_row}
            ).execute()
            
        except Exception as e:
            print(f"  Error saving to Sheets: {e}")
    
    def run_daily_research(self):
        """Main execution"""
        print("=" * 70)
        print("🎨 USA PRINTIFY/POD TREND FINDER")
        print("=" * 70)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        print("🔍 Finding trending topics in USA...")
        trends = self.find_trending_topics()
        print(f"  Found {len(trends)} trending topics")
        
        if not trends:
            print("\n⚠️  No trends found. Check Serper API key.")
            return
        
        print("\n🤖 Analyzing opportunities with Claude AI...")
        analysis = self.analyze_niche_opportunities(trends)
        
        print("\n📊 Extracting opportunities...")
        opportunities = self.extract_opportunities(analysis)
        print(f"  Extracted {len(opportunities)} niche opportunities")
        
        if opportunities:
            print("\n💾 Saving to Google Sheets...")
            self.save_to_sheets(opportunities, analysis)
            
            print("\n" + "=" * 70)
            print("🎯 TOP 3 OPPORTUNITIES")
            print("=" * 70)
            
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"\n{i}. {opp.get('niche', 'Unknown')}")
                print(f"   Audience: {opp.get('audience', 'N/A')}")
                print(f"   Demand: {opp.get('demand_score', 0)}/10")
                print(f"   Competition: {opp.get('competition', 'Unknown')}")
                print(f"   Products: {opp.get('products', 'N/A')}")
                print(f"   Est. Revenue: {opp.get('est_revenue', 'N/A')}")
        else:
            print("\n⚠️  Could not extract opportunities from analysis")
            print("\nRaw analysis:")
            print(analysis[:500] + "...")
        
        print("\n✅ Research complete!")
        print("\nNext steps:")
        print("1. Review opportunities in Google Sheets")
        print("2. Pick 1-2 niches to test")
        print("3. Create 3-5 designs per niche")
        print("4. Set up products in Printify")
        print("5. Run Facebook ads ($10-20/day per niche)")

if __name__ == "__main__":
    bot = PrintifyTrendFinder()
    bot.run_daily_research()
