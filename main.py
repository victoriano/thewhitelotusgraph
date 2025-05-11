"""
white_lotus_fetch_photos.py
————————————
Fill the `photo_url` column of white_lotus_nodes_with_photos_skeleton.csv
with the first infobox image on each character’s Fandom page
(https://thewhitelotus.fandom.com).
Requires: requests, beautifulsoup4, pandas, tqdm, polars
"""

import re, time, requests, pandas as pd, polars as pl
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm

# --- Configuration ---
CSV_NODES_INPUT = "characters_input_skeleton.csv"
CSV_EDGES_INPUT = "relationships_input.csv"
CSV_FINAL_OUTPUT = "output_character_relationships_with_details.csv"

# --- Constants ---
USER_AGENT = "Mozilla/5.0 (compatible; WhiteLotusScraper/1.0)"
HEADERS = {"User-Agent": USER_AGENT}

def correct_initial_input_urls(csv_path: str):
    """Updates wiki_page_url for specified characters directly in the input CSV (skeleton file)."""
    characters_to_update = [
        {"name": "Tanya McQuoid", "new_wiki_url": "https://thewhitelotus.fandom.com/wiki/Tanya_McQuoid-Hunt"},
        {"name": "Lucia", "new_wiki_url": "https://thewhitelotus.fandom.com/wiki/Lucia_Greco"},
        {"name": "Belinda", "new_wiki_url": "https://thewhitelotus.fandom.com/wiki/Belinda_Lindsey"}
    ]
    try:
        df = pl.read_csv(csv_path)
        print(f"ℹ️  Correcting initial URLs in {csv_path}...")
        for char_update in characters_to_update:
            char_name = char_update["name"]
            new_wiki_url = char_update["new_wiki_url"]
            df = df.with_columns([
                pl.when(pl.col("name") == char_name)
                .then(pl.lit(new_wiki_url))
                .otherwise(pl.col("wiki_page_url"))
                .alias("wiki_page_url")
            ])
            print(f"    ✏️  {char_name}: Set wiki_page_url to {new_wiki_url} in {csv_path}")
        df.write_csv(csv_path)
        print(f"✅  Finished correcting initial URLs. Saved to {csv_path}")
    except Exception as e:
        print(f"❌ Error during initial URL correction: {e}")

def first_static_image(page_url: str) -> str | None:
    """Return the https://static.wikia.nocookie.net/... image URL in the infobox."""
    r = requests.get(page_url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.content, "html.parser")

    # 1️⃣ Try infobox img
    img = soup.select_one("figure.pi-item.pi-image a.image-thumbnail img")
    if img and img.get("src"):
        full_url = img["src"]
        # The src URL might be a versioned one with /revision/... Remove that part.
        return full_url.split("/revision/")[0]
    return None

def main() -> pl.DataFrame | None:
    """Main function to read CSV, fetch photos, and return a Polars DataFrame."""
    try:
        df_nodes = pl.read_csv(CSV_NODES_INPUT)
        print(f"ℹ️  Read {len(df_nodes)} rows from {CSV_NODES_INPUT}")

        # Ensure 'photo_url' column exists and is initialized to None if not present, 
        # or if we want to ensure it's blank before fetching
        if "photo_url" not in df_nodes.columns:
            df_nodes = df_nodes.with_columns(pl.lit(None).alias("photo_url").cast(pl.String))
        else: # If it exists but we want to ensure it's treated as if it needs filling
            df_nodes = df_nodes.with_columns(pl.col("photo_url").cast(pl.String)) # Ensure correct type

        updated_rows = []
        for row in tqdm(df_nodes.iter_rows(named=True), total=len(df_nodes), desc="Fetching photos"):
            updated_row = row.copy() # Make a mutable copy
            if row["wiki_page_url"] and isinstance(row["wiki_page_url"], str):
                photo_url = first_static_image(row["wiki_page_url"])
                updated_row["photo_url"] = photo_url if photo_url else ""
            else:
                updated_row["photo_url"] = ""
            updated_rows.append(updated_row)
            time.sleep(0.1) # Be polite to the server

        df_filled_nodes = pl.DataFrame(updated_rows, schema=df_nodes.schema)
        # print(f"✅  Photo fetching complete. Data is in memory.") # No longer saving to CSV_OUT here
        print(f"✅  Photo fetching complete. {len(df_filled_nodes)} nodes processed. Data is in memory.")
        return df_filled_nodes
        
    except Exception as e:
        print(f"❌ Error in main photo fetching: {e}")
        return None


def merge_node_info_to_edges_corrected(df_nodes_filled: pl.DataFrame):
    """Merges photo_url and wiki_page_url from the nodes DataFrame into the edges file for both source and target nodes."""
    try:
        df_edges = pl.read_csv(CSV_EDGES_INPUT)
        print(f"ℹ️  Read {len(df_edges)} edges from {CSV_EDGES_INPUT}.")
        print(f"ℹ️  Using {len(df_nodes_filled)} nodes from in-memory DataFrame for merging.")

        # Prepare a separate DataFrame for source node information with renamed columns
        df_nodes_for_source_join = df_nodes_filled.select([
            pl.col("name").alias("source_join_key"),
            pl.col("wiki_page_url").alias("source_wiki_page_url"),
            pl.col("photo_url").alias("source_photo_url")
        ])

        # Prepare a separate DataFrame for target node information with renamed columns
        df_nodes_for_target_join = df_nodes_filled.select([
            pl.col("name").alias("target_join_key"),
            pl.col("wiki_page_url").alias("target_wiki_page_url"),
            pl.col("photo_url").alias("target_photo_url")
        ])
        
        # First join (source)
        df_merged_with_source = df_edges.join(
            df_nodes_for_source_join, # Use the fully prepared DataFrame
            left_on="source_label",
            right_on="source_join_key", # This key exists directly in df_nodes_for_source_join
            how="left"
        )

        # Second join (target)
        df_final_merged = df_merged_with_source.join(
            df_nodes_for_target_join, # Use the fully prepared DataFrame
            left_on="target_label",
            right_on="target_join_key", # This key exists directly in df_nodes_for_target_join
            how="left"
        )

        # Now, drop both temporary join keys at the very end
        # Ensure the keys exist before dropping, to avoid new errors if the join still fails before this point
        columns_to_drop = []
        if "source_join_key" in df_final_merged.columns:
            columns_to_drop.append("source_join_key")
        if "target_join_key" in df_final_merged.columns:
            columns_to_drop.append("target_join_key")
        
        df_to_write = df_final_merged.drop(columns_to_drop)

        df_to_write.write_csv(CSV_FINAL_OUTPUT)
        print(f"✅  Successfully merged source and target node info into edges. Saved to {CSV_FINAL_OUTPUT}")

    except Exception as e:
        print(f"❌ Error during corrected merge operation: {e}")

if __name__ == "__main__":
    correct_initial_input_urls(CSV_NODES_INPUT) # Correct URLs in the skeleton file first
    
    filled_nodes_df = main() # Fetch photos, returns a DataFrame
    
    if filled_nodes_df is not None:
        merge_node_info_to_edges_corrected(filled_nodes_df) # Merge with corrected & updated node data (DataFrame)
    else:
        print("❌ Photo fetching failed, skipping merge operation.")