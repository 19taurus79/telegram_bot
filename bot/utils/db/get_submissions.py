from bot_tables.tables import Submissions

async def get_submissions(id_product: str):
    submissions = await Submissions.select().where((Submissions.product==id_product)&(Submissions.different>0)&(Submissions.document_status=="затверджено")).order_by(Submissions.client)
    return submissions