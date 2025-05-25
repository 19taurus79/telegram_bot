from bot_tables.tables import ProductGuide

async def get_products(query: str):
    products = await ProductGuide.select().where(ProductGuide.product.ilike(f"%{query}%"))
    return products

async def get_product_by_id(id_product: str):
    product = await ProductGuide.select().where(ProductGuide.id==id_product)
    return product