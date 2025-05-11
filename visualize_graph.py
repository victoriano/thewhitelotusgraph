import polars as pl
import networkx as nx
from pyvis.network import Network
import os

# --- Configuration ---
CSV_FINAL_OUTPUT = "output_character_relationships_with_details.csv"
HTML_OUTPUT_FILENAME = "index.html" # Changed default output filename
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
    nt = Network(notebook=False, height="900px", width="100%", bgcolor="#F7F6F1", font_color="black")

    # Populate NetworkX graph first
    added_nodes_nx = set() # To track nodes added to nx_graph
    node_size = 60
    label_font_size = 20
    edge_font_size = 14

    for row in df_merged.iter_rows(named=True):
        source_name = row.get("source_label")
        target_name = row.get("target_label")
        source_photo = row.get("source_photo_url") or DEFAULT_IMAGE_PLACEHOLDER
        target_photo = row.get("target_photo_url") or DEFAULT_IMAGE_PLACEHOLDER
        relationship = row.get("relationship") or "related"

        # Add source node only if it's not already added and has a real photo
        if source_name and source_name not in added_nodes_nx:
            if source_photo != DEFAULT_IMAGE_PLACEHOLDER:
                nx_graph.add_node(source_name, label=source_name, shape="image", image=source_photo, title=source_name, size=node_size, font_size=label_font_size)
                added_nodes_nx.add(source_name)
        
        # Add target node only if it's not already added and has a real photo
        if target_name and target_name not in added_nodes_nx:
            if target_photo != DEFAULT_IMAGE_PLACEHOLDER:
                nx_graph.add_node(target_name, label=target_name, shape="image", image=target_photo, title=target_name, size=node_size, font_size=label_font_size)
                added_nodes_nx.add(target_name)
        
        # Add edge only if both source and target nodes have been added to the graph (i.e., they have real photos)
        if source_name and target_name and \
           source_name in added_nodes_nx and target_name in added_nodes_nx:
            nx_graph.add_edge(source_name, target_name, title=relationship, label=relationship, font_size=edge_font_size)

    # Calculate layout using NetworkX
    # k controls the optimal distance between nodes. Larger k = more spread.
    # iterations refine the layout.
    # seed ensures reproducible layouts.
    # pos = nx.spring_layout(nx_graph, k=12.0, iterations=550, seed=42) 
    # scaling_factor = 700 # This variable is now effectively the 'scale' for kamada_kawai
    pos = nx.kamada_kawai_layout(nx_graph, scale=1700) # Using existing scaling_factor for the scale parameter

    # Add nodes to pyvis network with pre-calculated fixed positions
    for node_id, (x, y) in pos.items():
        node_attrs = nx_graph.nodes[node_id]
        nt.add_node(
            node_id,
            x=x, # Coordinates from kamada_kawai_layout are already scaled
            y=y, # Coordinates from kamada_kawai_layout are already scaled
            fixed=True,
            label=node_attrs.get('label', node_id),
            shape="image", # Ensure shape is set
            image=node_attrs.get('image', DEFAULT_IMAGE_PLACEHOLDER),
            title=node_attrs.get('title', node_id),
            size=node_attrs.get('size', node_size),
            font={'size': node_attrs.get('font_size', label_font_size)} # Use stored font_size
        )

    # Add edges to pyvis network
    for source, target, edge_attrs in nx_graph.edges(data=True):
        nt.add_edge(
            source,
            target,
            title=edge_attrs.get('title', 'related'),
            label=edge_attrs.get('label', 'related'),
            font={'size': edge_attrs.get('font_size', edge_font_size)} # Use stored font_size
        )

    # Add physics toggle buttons to the UI
    # nt.show_buttons(filter_=['physics']) # Temporarily commented out for debugging

    # Set advanced layout and interaction options using a JSON string
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
        "enabled": false
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

        # Clean potential default pyvis elements from <head>
        head_start_index = html_content.find('<head>')
        head_end_index = html_content.find('</head>')

        if head_start_index != -1 and head_end_index != -1:
            head_content_start = head_start_index + len('<head>')
            actual_head_content = html_content[head_content_start:head_end_index]
            
            # Patterns pyvis might add to <head>
            pyvis_head_placeholders = [
                "<center><hr></center>",
                "<center><hr/></center>",
                "<center><h1></h1></center>",
                # Variants with newlines/indentation
                "<center>\n<hr>\n</center>",
                "<center>\n<hr/>\n</center>",
                "<center>\n<h1></h1>\n</center>",
            ]
            
            cleaned_head_content = actual_head_content
            for placeholder in pyvis_head_placeholders:
                cleaned_head_content = cleaned_head_content.replace(placeholder, "")
            
            if cleaned_head_content != actual_head_content:
                html_content = html_content[:head_content_start] + cleaned_head_content + html_content[head_end_index:]
                print("Cleaned default pyvis placeholders from <head>.")

        title_text = "The White Lotus Graph"
        styled_title_html = f'''<div class="container text-left mt-4 mb-2">
            <h1 style="font-family: 'Cinzel', serif; color: #333; font-size: 25px;">{title_text}</h1>
        </div>'''

        attribution_text = 'Vibecoded by <a href="https://linkedin.com/in/victorianoizquierdo" target="_blank" rel="noopener noreferrer" style="color: rgb(7, 81, 207); text-decoration: none;">Victoriano Izquierdo</a> from <a href="https://graphext.com" target="_blank" rel="noopener noreferrer" style="color: rgb(7, 81, 207); text-decoration: none;">Graphext</a>'
        attribution_html = f'''<div class="container text-left mb-4">
            <p style="font-family: 'Arial', sans-serif; font-size: 1rem; color: #555;">{attribution_text}</p>
        </div>'''

        # Ensure <head> exists, or add it (though cleaning implies it does)
        # Add Bootstrap CSS and Google Fonts CSS into the <head>
        # Re-find head_end_index as html_content might have changed during cleaning
        head_end_index = html_content.find('</head>') 
        if head_start_index != -1 and head_end_index != -1: # Check again in case head was malformed/removed by error
            # Ensure <head> tag itself wasn't removed if it was empty and cleaned to nothing
            if html_content.find('<head>') == -1:
                 # This case should be rare; if pyvis makes a head, it usually has other essential tags.
                 # If truly empty and removed, we'd need to reconstruct it or insert before <body>.
                 # For now, assume <head> tags persist.
                 pass 
            bootstrap_css = '<link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">'
            google_fonts_css = '<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400..900&display=swap" rel="stylesheet">'
            custom_styles_css = '''<style>
              body {
                background-color: #F7F6F1; /* Off-white background */
                margin: 0;
                padding: 0;
              }
              #mynetwork {
                border: none !important; /* Remove border from graph container */
              }
            </style>'''
            html_content = html_content[:head_end_index] + bootstrap_css + google_fonts_css + custom_styles_css + html_content[head_end_index:]
        else:
            print("Could not find </head> tag to insert Bootstrap, Google Fonts, and Custom CSS after cleaning.")

        # Combine title and attribution
        header_content = styled_title_html + attribution_html

        # Insert the styled title and attribution after the <body> tag
        body_tag_position = html_content.find('<body>')
        if body_tag_position != -1:
            body_tag_position += len('<body>')
            html_content = html_content[:body_tag_position] + header_content + html_content[body_tag_position:]
        else:
            print("Could not find <body> tag to insert title and attribution.")

        with open(HTML_OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Title and attribution added to {HTML_OUTPUT_FILENAME}")
        print(f"You can open this file in your web browser to view the interactive graph.")
    except Exception as e:
        print(f"Error saving graph or adding title: {e}")

if __name__ == "__main__":
    create_graph_visualization()
