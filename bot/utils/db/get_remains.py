from bot_tables.tables import Remains

async def get_remains(id_product: str):
    remains = await Remains.select().where((Remains.product==id_product)&(Remains.buh>0))
    return remains