import os
import logging
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import SessionLocal  # Assuming SessionLocal is in database.py

# from dotenv import load_dotenv # No longer needed here for DND_DATA_FILE_PATH
from app.utils.read_data import load_dnd_data

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_static_data(db: Session):
    """
    Populates static D&D data (races, classes, spells, features, proficiencies)
    from dnd_data.json into the database if it doesn't already exist.
    Data is loaded using the load_dnd_data utility function.
    """
    data = load_dnd_data()

    if not data:
        logging.error(
            "Failed to load D&D data. Static data initialization will be skipped."
        )
        return

    # Helper to add item if not exists
    def add_if_not_exists(db: Session, model_class, item_id, **kwargs):
        # Check if item with the same ID already exists
        if db.query(model_class).filter(model_class.id == item_id).first():
            return False  # Item with this ID already exists

        # For models with a unique 'name' constraint, also check if an item with the same name exists
        if hasattr(model_class, "name") and "name" in kwargs:
            if db.query(model_class).filter(model_class.name == kwargs["name"]).first():
                logging.warning(
                    f"Skipping insertion for {model_class.__name__} with name '{kwargs['name']}' due to duplicate name."
                )
                return False  # Item with this name already exists

        # If neither ID nor name (for relevant models) exists, add the new item
        db_item = model_class(id=item_id, **kwargs)
        db.add(db_item)
        return True

    # Populate Races
    if "races" in data:
        logging.info("Populating races...")
        for id_str, name_str in data["races"].items():
            add_if_not_exists(db, models.Race, item_id=int(id_str), name=name_str)

    # Populate Classes (DndClass)
    if "classes" in data:
        logging.info("Populating classes...")
        for id_str, name_str in data["classes"].items():
            add_if_not_exists(db, models.DndClass, item_id=int(id_str), name=name_str)

    # Populate Spells
    if "spells" in data:
        logging.info("Populating spells...")
        for id_str, name_str in data["spells"].items():
            # Assuming spells in JSON only have name. Add other fields if available.
            # For now, level and description will be null as per model.
            add_if_not_exists(db, models.Spell, item_id=int(id_str), name=name_str)

    # Populate Features
    if "features" in data:
        logging.info("Populating features...")
        for id_str, name_str in data["features"].items():
            # Assuming features in JSON only have name. Add description if available.
            add_if_not_exists(db, models.Feature, item_id=int(id_str), name=name_str)

    # Populate Proficiencies
    if "proficiencies" in data:
        logging.info("Populating proficiencies...")
        for id_str, name_str in data["proficiencies"].items():
            # Assuming proficiencies in JSON only have name. Add type if available.
            add_if_not_exists(
                db, models.Proficiency, item_id=int(id_str), name=name_str
            )

    try:
        db.commit()
        logging.info("Static data commit successful.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error committing static data: {e}")


def try_initialize_static_data():
    """
    Creates a new DB session and attempts to initialize static data.
    To be called at application startup.
    """
    db = SessionLocal()
    try:
        logging.info("Attempting to initialize static D&D data...")
        initialize_static_data(db)
        logging.info("Static D&D data initialization check complete.")
    except Exception as e:
        logging.error(
            f"An error occurred during static data initialization: {e}", exc_info=True
        )
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # This allows running the script directly to populate data
    # Ensure your DATABASE_URL is set correctly in .env or environment
    logging.info("Running init_db.py directly...")
    from dotenv import load_dotenv

    # Load .env from the backend directory
    dotenv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"
    )
    load_dotenv(dotenv_path=dotenv_path)

    # Need to ensure engine is created for SessionLocal if not already
    # This might require importing or re-creating engine setup from database.py
    # For simplicity, assuming SessionLocal() works if database.py is correct

    try_initialize_static_data()
