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



##Här gör jag en funktion för att få fram leverantörsinformation från SupplierID.
def get_supplier_info(supplier_id):
    for supplier in suppliers_data:
        if supplier['SupplierID'] == supplier_id:
            return supplier['ContactName'], supplier['Phone'], supplier['CompanyName']


##Samma query som är i Notebook över produkter som behöver beställas.
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
# Visning av produkter
elif selection == "Produkter":
    st.title("Alla Våra Produkter")
    products_to_display = list(collection.find())  # Hämtar alla produkter
    for product in products_to_display:
        st.write(f"**Produkt:** {product['ProductName']}")
        st.write(f"**Leverantör:** {product['SupplierName']}")
        st.write(f"**Kontaktperson:** {product['ContactName']}")
        st.write(f"**Telefon:** {product['Phone']}")
        st.write('---')

# Visning av leverantörer
elif selection == "Leverantörer":
    st.title("Alla Leverantörer")
    
    # Hämta alla unika leverantörer
    suppliers_to_display = list(collection.aggregate([
        {"$group": {"_id": "$SupplierName", 
                    "ContactName": {"$first": "$ContactName"},
                    "Phone": {"$first": "$Phone"},
                    "count": {"$sum": 1}}}
    ]))  # Gruppér leverantörerna och samla kontaktinformation
    
    # Sortera leverantörerna alfabetiskt baserat på deras namn
    suppliers_to_display_sorted = sorted(suppliers_to_display, key=lambda x: x['_id'])
    
    if suppliers_to_display_sorted:
        for supplier in suppliers_to_display_sorted:
            st.write(f"**Leverantör:** {supplier['_id']}")
            st.write(f"**Kontaktperson:** {supplier['ContactName']}")
            st.write(f"**Telefon:** {supplier['Phone']}")
            st.write(f"**Antal produkter:** {supplier['count']}")
            st.write('---')
    else:
        st.write("Inga leverantörer funna.")




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
        # Skapa listor för produktnamn och lagerstatus för att kunna plotta
        product_names = [product['ProductName'] for product in products_to_order]
        stock_in_hand = [product['UnitsInStock'] for product in products_to_order]
        reorder_levels = [product['ReorderLevel'] for product in products_to_order]
        
        # Beräkna hur mycket som behöver beställas
        reorder_needed = [max(0, reorder_levels[i] - stock_in_hand[i]) for i in range(len(products_to_order))]
        
        # Skapa en bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        index = np.arange(len(product_names))
        bar_width = 0.35
        
        bars1 = ax.bar(index, stock_in_hand, bar_width, label='Enheter i lager')
        bars2 = ax.bar(index + bar_width, reorder_needed, bar_width, label='Enheter att beställa')
        
        # Lägg till etiketter och titel
        ax.set_xlabel('Produkter')
        ax.set_ylabel('Antal Enheter')
        ax.set_title('Lagersaldo för produkter som behöver beställas')
        ax.set_xticks(index + bar_width / 2)
        ax.set_xticklabels(product_names, rotation=45, ha="right")
        ax.legend()

        # Visa diagrammet
        st.pyplot(fig)

        # Visa produktdetaljer nedanför diagrammet
        for product in products_to_order:
            st.write(f"**Produkt:** {product['ProductName']}")
            st.write(f"**Enheter i lager:** {product['UnitsInStock']}")
            st.write(f"**Units on order:** {product['UnitsOnOrder']}")
            st.write(f"**Beställningsnivå (Reorder Level):** {product['ReorderLevel']}")
            st.write(f"**Leverantör:** {product['SupplierName']}")
            st.write(f"**Kontaktperson:** {product['ContactName']}")
            st.write(f"**Telefon:** {product['Phone']}")
            st.write('---')
    else:
        st.write("Inga produkter behöver beställas just nu.")