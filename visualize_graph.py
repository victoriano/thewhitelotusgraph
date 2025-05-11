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

        # Post-process HTML to add a styled title
        with open(HTML_OUTPUT_FILENAME, 'r', encoding='utf-8') as f:
            html_content = f.read()

        title_text = "The White Lotus Character Relationships"
        # Using Bootstrap's display heading for a nicer look, centered in a container
        styled_title_html = f'''<div class="container text-center mt-3 mb-3">
            <h1 class="display-4">{title_text}</h1>
        </div>'''
        
        # PyVis creates an empty <center><h1></h1></center> when no heading is specified.
        # We will replace this placeholder.
        # The exact structure might vary slightly with pyvis versions, being flexible here.
        placeholder_variants = [
            "<center>\n<h1></h1>\n</center>",
            "<center><h1></h1></center>", # If no newlines
            "<center>\n  <h1></h1>\n</center>" # If indented
        ]

        replaced = False
        for placeholder in placeholder_variants:
            if placeholder in html_content:
                html_content = html_content.replace(placeholder, styled_title_html, 1)
                replaced = True
                break
        
        if not replaced:
            # As a fallback, try to insert after <body> if the specific placeholder isn't found
            body_tag_end = html_content.find("<body>")
            if body_tag_end != -1:
                insert_point = body_tag_end + len("<body>")
                html_content = html_content[:insert_point] + "\n" + styled_title_html + html_content[insert_point:]
                print("ℹ️  Used fallback method to insert title.")
            else:
                print("⚠️  Could not find a suitable place to insert the title.")

        with open(HTML_OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"ℹ️  Title added to {HTML_OUTPUT_FILENAME}")
        print(f"ℹ️  You can open this file in your web browser to view the interactive graph.")
    except Exception as e:
        print(f"❌ Error saving graph or adding title: {e}")

if __name__ == "__main__":
    create_graph_visualization()
