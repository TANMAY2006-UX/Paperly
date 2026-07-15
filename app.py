from flask import Flask, render_template, abort
import re
from models.paper import Paper

app = Flask(__name__)

# Custom Jinja filter to render {{figure_x}} placeholders
@app.template_filter('render_figures')
def render_figures(content, figures_dict):
    if not content:
        return ""
    
    def replace_figure(match):
        fig_id = match.group(1)
        figure = figures_dict.get(fig_id)
        if not figure:
            return f'<div class="figure-missing">[Figure {fig_id} missing]</div>'
            
        caption = figure.get('caption', '')
        # Simple extraction of "Figure X:" for styling
        prefix = ""
        rest_caption = caption
        caption_match = re.match(r'^(Figure\s+\d+:?)(.*)$', caption, re.IGNORECASE)
        if caption_match:
            prefix = caption_match.group(1)
            rest_caption = caption_match.group(2)
            
        img_path = figure.get('image_path', '')
        # Fix paths for url_for static if needed, or just relative
        if img_path.startswith('static/'):
            img_path = '/' + img_path
            
        return f'''
        <figure class="paper-figure" id="{fig_id}" data-figure-id="{fig_id}">
            <div class="figure-image-wrapper">
                <img src="{img_path}" alt="{caption}" loading="lazy" class="figure-img">
                <div class="figure-skeleton skeleton"></div>
            </div>
            <figcaption>
                <span class="caption-prefix">{prefix}</span>{rest_caption}
                <button class="expand-fig-btn" aria-label="Expand figure">⤢</button>
            </figcaption>
        </figure>
        '''
        
    # Replace {{figure_xyz}} with HTML
    return re.sub(r'\{\{(figure_[a-zA-Z0-9_]+)\}\}', replace_figure, content)

@app.route('/')
def index():
    papers = Paper.get_all()
    
    # Define curated categories with SVGs
    curated_categories = [
        {
            "id": "artificial-intelligence",
            "name": "Artificial Intelligence",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>'
        },
        {
            "id": "computer-networks",
            "name": "Computer Networks",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>'
        },
        {
            "id": "databases",
            "name": "Databases",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>'
        },
        {
            "id": "systems-os",
            "name": "Systems & OS",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>'
        },
        {
            "id": "hci-design",
            "name": "HCI & Design",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19l7-7 3 3-7 7-3-3z"></path><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"></path><path d="M2 2l7.586 7.586"></path><circle cx="11" cy="11" r="2"></circle></svg>'
        },
        {
            "id": "personal-collection",
            "name": "Personal Collection",
            "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>'
        }
    ]
    
    # Compute counts
    for cat in curated_categories:
        count = sum(1 for p in papers if p.get('category') and p['category'].lower() == cat['name'].lower())
        cat['count'] = count
        
    return render_template('home.html', papers=papers, categories=curated_categories)

@app.route('/papers/<slug>')
def paper_reader(slug):
    paper = Paper.get_by_slug(slug)
    if not paper:
        abort(404)
        
    return render_template('reader.html', paper=paper)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
