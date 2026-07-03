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
    return render_template('home.html')

@app.route('/papers/<slug>')
def paper_reader(slug):
    paper = Paper.get_by_slug(slug)
    if not paper:
        abort(404)
        
    return render_template('reader.html', paper=paper)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
