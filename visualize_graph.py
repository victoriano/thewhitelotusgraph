import polars as pl
import networkx as nx
from pyvis.network import Network
import os

# --- Configuration ---
CSV_FINAL_OUTPUT = "output_character_relationships_with_details.csv"
HTML_OUTPUT_FILENAME = "white_lotus_graph.html"
DEFAULT_IMAGE_PLACEHOLDER = "https://via.placeholder.com/150/CCCCCC/000000?Text=No+Image" # A placeholder if no image is found

def create_graph_visualization():
    """Reads the merged data and creates an interactive graph visualization."""
    if not os.path.exists(CSV_FINAL_OUTPUT):
        print(f"❌ Error: Input file {CSV_FINAL_OUTPUT} not found. Please run the main script first.")
        return

    try:
        df_merged = pl.read_csv(CSV_FINAL_OUTPUT)
        print(f"ℹ️  Read {len(df_merged)} relationships from {CSV_FINAL_OUTPUT}.")
    except Exception as e:
        print(f"❌ Error reading {CSV_FINAL_OUTPUT}: {e}")
        return

    # Create a NetworkX graph
    nx_graph = nx.Graph()
    
    # Pyvis Network
    # Adjusted height and width for better initial display
    nt = Network(notebook=False, height="900px", width="100%")

    # Add nodes with images and labels
    # Keep track of added nodes to avoid duplicates and to add all unique characters
    added_nodes = set()
    node_size = 60  # Increased node size for bigger pictures
    label_font_size = 20 # Increased label font size
    edge_font_size = 14 # Font size for edge labels

    for row in df_merged.iter_rows(named=True):
        source_name = row.get("source_label")
        target_name = row.get("target_label")
        source_photo = row.get("source_photo_url") or DEFAULT_IMAGE_PLACEHOLDER
        target_photo = row.get("target_photo_url") or DEFAULT_IMAGE_PLACEHOLDER
        relationship = row.get("relationship") or "related"

        if source_name and source_name not in added_nodes:
            nt.add_node(source_name, label=source_name, shape="image", image=source_photo, title=source_name, size=node_size, font={'size': label_font_size})
            added_nodes.add(source_name)
        
        if target_name and target_name not in added_nodes:
            nt.add_node(target_name, label=target_name, shape="image", image=target_photo, title=target_name, size=node_size, font={'size': label_font_size})
            added_nodes.add(target_name)
        
        if source_name and target_name:
            nt.add_edge(source_name, target_name, title=relationship, label=relationship, font={'size': edge_font_size})

    # Add some physics options for a better layout
    nt.set_options("""
    {
      "nodes": {
        "font": {
          "size": 18
        }
      },
      "edges": {
        "font": {
          "size": 12,
          "align": "top"
        },
        "arrows": {
          "to": { "enabled": false }
        }
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -40000,
          "centralGravity": 0.25,
          "springLength": 100,
          "springConstant": 0.05,
          "damping": 0.3,
          "avoidOverlap": 0.8
        },
        "minVelocity": 0.75,
        "solver": "barnesHut"
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200
      }
    }
    """)

    try:
        nt.save_graph(HTML_OUTPUT_FILENAME)
        print(f"✅  Graph visualization saved to {HTML_OUTPUT_FILENAME}")

        # Post-process HTML to add a styled title and attribution
        with open(HTML_OUTPUT_FILENAME, 'r', encoding='utf-8') as f:
            html_content = f.read()

        title_text = "Unraveling The White Lotus: A Character Web"
        styled_title_html = f'''<div class="container text-center mt-4 mb-2">
            <h1 class="display-4" style="font-family: 'Georgia', serif; color: #333;">{title_text}</h1>
        </div>'''

        attribution_text = 'Vibecoded by <a href="https://linkedin.com/in/victorianoizquierdo" target="_blank" rel="noopener noreferrer" style="color: #007bff; text-decoration: none;">Victoriano Izquierdo</a>'
        attribution_html = f'''<div class="container text-center mb-4">
            <p style="font-family: 'Arial', sans-serif; font-size: 1rem; color: #555;">{attribution_text}</p>
        </div>'''

        # Ensure <head> exists, or add it
        if '<head>' not in html_content:
            # Fallback: insert a basic head if not present (pyvis usually creates one)
            html_content = html_content.replace('<html>', '<html><head></head>', 1)
            
        # Insert Bootstrap CSS into the <head>
        bootstrap_css = '<link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">'
        head_tag_position = html_content.find('</head>')
        if head_tag_position != -1:
            html_content = html_content[:head_tag_position] + bootstrap_css + html_content[head_tag_position:]
        else:
            print("⚠️  Could not find </head> tag to insert Bootstrap CSS.")

        # Combine title and attribution
        header_content = styled_title_html + attribution_html

        # Insert the styled title and attribution after the <body> tag
        body_tag_position = html_content.find('<body>')
        if body_tag_position != -1:
            body_tag_position += len('<body>')
            html_content = html_content[:body_tag_position] + header_content + html_content[body_tag_position:]
        else:
            print("⚠️  Could not find <body> tag to insert title and attribution.")

        with open(HTML_OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"ℹ️  Title and attribution added to {HTML_OUTPUT_FILENAME}")
        print(f"ℹ️  You can open this file in your web browser to view the interactive graph.")
    except Exception as e:
        print(f"❌ Error saving graph or adding title: {e}")

if __name__ == "__main__":
    create_graph_visualization()
