from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import MongoClient
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json

uri = "mongodb+srv://kymiajm:kjZHL1KzsPnTHzGd@cluster0.adcuj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

##Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

##Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

database = client["Database"]
collection = database["Products"]

products_df = pd.read_csv('/Users/k/Documents/TUC/DatabaseTypes/Assignment_01/data/northwind/products.csv')
with open('/Users/k/Documents/TUC/DatabaseTypes/Assignment_01/data/northwind/suppliers.json', 'r') as f:
    suppliers_data = json.load(f)
    
suppliers_dict = {supplier['SupplierID']: supplier for supplier in suppliers_data}

def merge_product_with_supplier(row):
    supplier_info = suppliers_dict.get(row['SupplierID'])
    if supplier_info:
        row['SupplierName'] = supplier_info['CompanyName']
        row['ContactName'] = supplier_info['ContactName']
        row['Phone'] = supplier_info['Phone']
    return row

products_df = products_df.apply(merge_product_with_supplier, axis=1)
documents = products_df.to_dict(orient='records')



## Här gör jag en funktion för att få fram leverantörsinformation från SupplierID.
def get_supplier_info(supplier_id):
    for supplier in suppliers_data:
        if supplier['SupplierID'] == supplier_id:
            return supplier['ContactName'], supplier['Phone'], supplier['CompanyName']


## Samma query som är i Notebook över produkter som behöver beställas.
def get_products_to_order():
    query = {
        "$expr": {
            "$gt": [
                "$ReorderLevel", 
                { "$add": ["$UnitsInStock", "$UnitsOnOrder"] }
            ]
        }
    }
    return list(collection.find(query))


## design & funktioner
###########################
st.sidebar.title("Navigera")
selection = st.sidebar.selectbox("Välj en sida:", ["Startsida", "Produkter", "Leverantörer", "Lagersaldo"])

# Startsida
if selection == "Startsida":
    st.title("Välkommen till Lagerhantering Appen!")
    st.write("""
        Här hjälper vi dig att hålla koll på dina produkter samt deras leverantörer och lagersaldon. 
        
        För att komma igång väljer du det du vill kolla :
        - **Produkter**: Visar alla produkter som finns i lager.
        - **Leverantörer**: Visar en lista på alla leverantörer som tillhandahåller produkter.
        - **Lagersaldo**: Visar produkter som behöver beställas baserat på lagernivå.
    """)
    st.image('/Users/k/Documents/TUC/DatabaseTypes/Assignment_01/images/stock_mngmnt.png', use_column_width=True)
    
## Produkter
elif selection == "Produkter":

    ## skapar två kolumner så att vi kan ha titlen och bild på en och samma rad
    col1, col2 = st.columns([4, 1]) 
    with col1: ## vänstra kolumn - där vi vill ha vår text
        st.title("Alla  Våra Produkter")
        
    with col2: ## högra kolumn - där vi vill ha vår bild
        st.image("/Users/k/Documents/TUC/DatabaseTypes/Assignment_01/images/products.png", width=80)

    products_to_display = list(collection.find())  # Hämtar alla produkter
    for product in products_to_display:
        st.write(f"**Produkt:** {product['ProductName']}")
        st.write(f"**Leverantör:** {product['SupplierName']}")
        st.write(f"**Kontaktperson:** {product['ContactName']}")
        st.write(f"**Telefon:** {product['Phone']}")
        st.write('---')

## Leverantörer
elif selection == "Leverantörer":
    
    ## skapar två kolumner så att vi kan ha titlen och bild på en och samma rad
    col1, col2 = st.columns([4, 1]) 
    with col1: ## vänstra kolumn - där vi vill ha vår text
        st.title("Alla Leverantörer")
        
    with col2: ## högra kolumn - där vi vill ha vår bild
        st.image("/Users/k/Documents/TUC/DatabaseTypes/Assignment_01/images/suppliers.png", width=80)
    
    suppliers_to_display = list(collection.aggregate([ ## gämtar all info för våra unika levarntörer
        {"$group": {"_id": "$SupplierName", 
                    "ContactName": {"$first": "$ContactName"},
                    "Phone": {"$first": "$Phone"},
                    "count": {"$sum": 1}}}
    ]))  
    
    
    suppliers_to_display_sorted = sorted(suppliers_to_display, key=lambda x: x['_id']) ## sorterar alfabetisk ordning
    
    if suppliers_to_display_sorted:
        for supplier in suppliers_to_display_sorted:
            st.write(f"**Leverantör:** {supplier['_id']}")
            st.write(f"**Kontaktperson:** {supplier['ContactName']}")
            st.write(f"**Telefon:** {supplier['Phone']}")
            st.write(f"**Antal produkter:** {supplier['count']}")
            st.write('---')
    else:
        st.write("Inga leverantörer funna.")


## Lagersaldo
elif selection == "Lagersaldo":
    st.title("Produkter som behöver beställas!")
    
    # Hämta alla produkter från MongoDB
    products_to_display = list(collection.find())
    
    # Filtrera produkter som behöver beställas
    products_to_order = [
        product for product in products_to_display 
        if product['ReorderLevel'] > (product['UnitsInStock'] + product['UnitsOnOrder'])
    ]
    
    
    if products_to_order:
        ## lista för de som skall plottas 
        product_names = [product['ProductName'] for product in products_to_order]
        stock_in_hand = [product['UnitsInStock'] for product in products_to_order]
        reorder_levels = [product['ReorderLevel'] for product in products_to_order]
        
        ## beräkning för beställning
        reorder_needed = [max(0, reorder_levels[i] - stock_in_hand[i]) for i in range(len(products_to_order))]
        
        ## bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        index = np.arange(len(product_names))
        bar_width = 0.35

        # färger för staplarna så att det matchar med bilden på startsidan 
        color1 = '#FF7043'  # Orangearosa
        color2 = '#D500F9'  # Rosalila

        bars1 = ax.bar(index, stock_in_hand, bar_width, label='Enheter i lager', color=color1)
        bars2 = ax.bar(index + bar_width, reorder_needed, bar_width, label='Enheter att beställa', color=color2)

        ax.set_xlabel('Produkter')
        ax.set_ylabel('Antal Enheter')
        ax.set_title('Lagersaldo för produkter som behöver beställas')
        ax.set_xticks(index + bar_width / 2)
        ax.set_xticklabels(product_names, rotation=45, ha="right")
        ax.legend()
        
        st.pyplot(fig)
        
        for product in products_to_order:
            st.write(f"**Produkt:** {product['ProductName']}")
            st.write(f"**Enheter i lager:** {product['UnitsInStock']}")
            st.write(f"**Antal enheter beställda:** {product['UnitsOnOrder']}")
            st.write(f"**Beställningsnivå:** {product['ReorderLevel']}")
            st.write(f"**Leverantör:** {product['SupplierName']}")
            st.write(f"**Kontaktperson:** {product['ContactName']}")
            st.write(f"**Telefon:** {product['Phone']}")
            st.write('---')
    else:
        st.write("Inga produkter behöver beställas just nu.")