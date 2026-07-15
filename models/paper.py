import json
import os
import re
import math
from database import get_db

class Paper:
    def __init__(self, db_row, json_content):
        self.id = db_row['id']
        self.title = db_row['title']
        self.authors = json.loads(db_row['authors'])
        self.year = db_row['year']
        self.venue = db_row['venue']
        
        self.abstract = json_content.get('abstract', '')
        self.keywords = json_content.get('keywords', [])
        
        # Process sections to add URL-safe IDs and map figures
        self.figures = {f['id']: f for f in json_content.get('figures', [])}
        self.tables = []
        self.visuals = []
        self.sections, self.supplementary_sections = self._process_sections(json_content.get('sections', []))
        self.total_word_count = sum(s.get('word_count', 0) for s in self.sections)
        self.reading_time_minutes = db_row['reading_time_minutes']
        self.references = json_content.get('references', []) # Future-proofing

    def _process_sections(self, raw_sections):
        processed = []
        supplementary = []
        references_section = None
        in_supplementary = False

        for index, section in enumerate(raw_sections):
            if section.get('title') == 'References':
                references_section = section
                in_supplementary = True
                continue
                
            # Create a URL-safe ID if not present
            section_id = f"section-{index}"
            if section.get('number'):
                section_id = f"section-{section['number'].replace('.', '-')}"
            elif section.get('title'):
                safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', section['title']).strip('-').lower()
                section_id = f"section-{safe_title}"
            
            section['id'] = section_id
            section['data_level'] = section.get('level', 1)
            
            # Content preprocessing
            raw_content = section.get('content', '')
            
            # Compute word_count: exclude figures and citations
            cleaned_content = re.sub(r'\{\{figure_\d+\}\}', '', raw_content)
            cleaned_content = re.sub(r'\[([0-9\s,\-]+)\]', '', cleaned_content)
            section['word_count'] = len(re.findall(r'\w+', cleaned_content))
            
            section['content'] = self._parse_content(raw_content)
            
            if in_supplementary:
                supplementary.append(section)
            else:
                processed.append(section)
            
        # Second pass: compute has_children and parent_id
        self._compute_hierarchy(processed)
        self._compute_hierarchy(supplementary)
            
        self.structured_references = self._parse_references(references_section) if references_section else []
        
        return processed, supplementary

    def _compute_hierarchy(self, sections_list):
        for i, section in enumerate(sections_list):
            level = section['data_level']
            number = str(section.get('number', ''))
            
            # 1. parent_id
            parent_id = None
            if number and '.' in number:
                parent_num = '.'.join(number.split('.')[:-1])
                parent_id = f"section-{parent_num.replace('.', '-')}"
            elif level > 1:
                # Fallback for sections without numbers
                for j in range(i - 1, -1, -1):
                    if sections_list[j]['data_level'] == level - 1:
                        parent_id = sections_list[j]['id']
                        break
            section['parent_id'] = parent_id
            
            # 2. has_children
            has_children = False
            for j in range(i + 1, len(sections_list)):
                if sections_list[j]['data_level'] <= level:
                    break
                if sections_list[j]['data_level'] == level + 1:
                    has_children = True
                    break
            section['has_children'] = has_children

    def _parse_content(self, raw_content):
        # Basic markdown bold/italic
        raw_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', raw_content)
        raw_content = re.sub(r'(?<![a-zA-Z0-9])\*(?!\s)([^\*\n]+?)(?<!\s)\*(?![a-zA-Z0-9])', r'<em>\1</em>', raw_content)
        
        # Split by double newline to get paragraphs/blocks
        blocks = re.split(r'\n\n+', raw_content.strip())
        parsed_blocks = []
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            # Check if block is a markdown table
            if block.startswith('|') and '\n|' in block:
                parsed_blocks.append(self._parse_markdown_table(block))
            else:
                # Process citations like [1] or [1, 2, 3] or [12-15]
                def replace_citation(match):
                    cite_text = match.group(1)
                    # For simplicity in V1, just wrap the whole thing. In V2, parse individual numbers.
                    # Create anchor links for each number found
                    numbers = re.findall(r'\d+', cite_text)
                    if numbers:
                        links = []
                        for n in numbers:
                            links.append(f'<a href="#ref-{n}" class="cite-link">{n}</a>')
                        # Reconstruct the citation format but with links
                        # This is a basic approach. A more robust one would replace numbers directly.
                        replaced_text = cite_text
                        for n in numbers:
                            replaced_text = re.sub(rf'\b{n}\b', f'<a href="#ref-{n}" class="cite-link">{n}</a>', replaced_text, count=1)
                        return f'<sup class="citation">[{replaced_text}]</sup>'
                    return f'<sup class="citation">[{cite_text}]</sup>'
                
                block_with_cites = re.sub(r'\[([0-9\s,\-]+)\]', replace_citation, block)
                
                # Track figures for visuals drawer
                def track_figures(match):
                    fig_id = match.group(1)
                    if fig_id in self.figures:
                        fig = self.figures[fig_id]
                        if not any(v.get('id') == fig_id for v in self.visuals):
                            
                            # Safely extract caption text without 'Figure X: ' prefix if present
                            caption = fig.get('caption', '').strip()
                            fig_number = str(fig.get('number', '')).strip()
                            
                            import re
                            # Match "Figure 1:", "Figure 1.", "Figure 1 - " etc.
                            m = re.match(r'^Figure\s+([a-zA-Z0-9]+)[\s:.\-]*\s*(.*)', caption, re.IGNORECASE)
                            if m:
                                if not fig_number:
                                    fig_number = m.group(1)
                                caption = m.group(2).strip()

                            title = f"Figure {fig_number}".strip()

                            self.visuals.append({
                                'id': fig_id,
                                'type': 'figure',
                                'title': title,
                                'caption': caption,
                                'image_path': fig.get('image_path')
                            })
                    return match.group(0)
                
                block_with_cites = re.sub(r'\{\{(figure_[a-zA-Z0-9_]+)\}\}', track_figures, block_with_cites)
                
                # Wrap in <p> if it's not already HTML or a figure placeholder
                if not block_with_cites.startswith('<') and not block_with_cites.startswith('{{figure'):
                    parsed_blocks.append(f'<p>{block_with_cites}</p>')
                else:
                    parsed_blocks.append(block_with_cites)
                    
        return '\n'.join(parsed_blocks)

    def _parse_markdown_table(self, block):
        lines = block.split('\n')
        if len(lines) < 2:
            return f'<p>{block}</p>'
            
        table_number = len(self.tables) + 1
        table_id = f"table-{table_number}"
        
        table_info = {
            'id': table_id,
            'type': 'table',
            'title': f"Table {table_number}"
        }
        self.tables.append(table_info)
        self.visuals.append(table_info)
            
        html = [f'<div class="table-responsive" id="{table_id}"><table>']
        preview_html = ['<div class="visual-table-preview"><table>']
        data_rows_seen = 0
        
        for i, line in enumerate(lines):
            line = line.strip().strip('|')
            cells = [cell.strip() for cell in line.split('|')]
            
            if i == 0:
                html.append('<thead><tr>')
                preview_html.append('<thead><tr>')
                for cell in cells:
                    html.append(f'<th>{cell}</th>')
                    preview_html.append(f'<th>{cell}</th>')
                html.append('</tr></thead><tbody>')
                preview_html.append('</tr></thead><tbody>')
            elif i == 1 and all(set(cell.strip('-: ')) == set() or not cell.strip('-: ') for cell in cells):
                continue
            else:
                html.append('<tr>')
                row_preview = ['<tr>']
                for cell in cells:
                    is_numeric = re.match(r'^[\d.,%+-]+$', cell)
                    align_class = ' class="numeric"' if is_numeric else ''
                    html.append(f'<td{align_class}>{cell}</td>')
                    row_preview.append(f'<td{align_class}>{cell}</td>')
                html.append('</tr>')
                row_preview.append('</tr>')
                
                if data_rows_seen < 2:
                    preview_html.extend(row_preview)
                data_rows_seen += 1
                
        html.append('</tbody></table></div>')
        preview_html.append('</tbody></table><div class="table-preview-fade"></div></div>')
        
        table_info['preview_html'] = '\n'.join(preview_html)
        return '\n'.join(html)
        
    def _parse_references(self, ref_section):
        raw_content = ref_section.get('content', '')
        references = []
        
        # Match lines like "* [1] Author..." or "[1] Author..."
        for line in raw_content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Try to match [N] at start or after a bullet
            match = re.search(r'\[(\d+)\]\s*(.*)', line)
            if match:
                num = match.group(1)
                text = match.group(2)
                
                # Extract simple URL if present
                url_match = re.search(r'(https?://[^\s]+)', text)
                url = url_match.group(1) if url_match else None
                
                references.append({
                    'id': f'ref-{num}',
                    'number': int(num),
                    'text': text,
                    'url': url
                })
        
        # Sort by number to be safe
        references.sort(key=lambda x: x['number'])
        return references

    @classmethod
    def get_all(cls):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, authors, year, venue, reading_time_minutes, category, keywords, added_at FROM papers ORDER BY added_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        papers = []
        for row in rows:
            papers.append({
                'id': row['id'],
                'slug': row['id'],
                'title': row['title'],
                'authors': json.loads(row['authors']) if row['authors'] else [],
                'year': row['year'],
                'venue': row['venue'],
                'reading_time_minutes': row['reading_time_minutes'],
                'category': row['category'],
                'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                'added_at': row['added_at']
            })
            
        return papers

    @staticmethod
    def get_by_slug(slug):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE id = ?", (slug,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        json_path = row['json_path']
        if not os.path.exists(json_path):
            return None
            
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
            
        return Paper(row, json_content)
