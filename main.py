from src.extract import extract_data
from src.transform import transform_data
from src.load import load_data

def run_etl():
    print("Starting ETL Pipeline...")
    
    # 1. data  Extract
    raw_data = extract_data("data/raw/source.csv")
    
    #  2. data Transform
    clean_data = transform_data(raw_data)
    
    # 3. final data Loadin to the destination location 
    load_data(clean_data, "data/processed/target.csv")
    
    print("ETL Pipeline completed successfully!")

if __name__ == "__main__":
    run_etl()
