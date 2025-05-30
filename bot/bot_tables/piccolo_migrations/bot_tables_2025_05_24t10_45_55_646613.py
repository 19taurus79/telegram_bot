from piccolo.apps.migrations.auto.migration_manager import MigrationManager


ID = "2025-05-24T10:45:55:646613"
VERSION = "1.26.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="", description=DESCRIPTION
    )

    def run():
        print(f"running {ID}")

    manager.add_raw(run)

    return manager
