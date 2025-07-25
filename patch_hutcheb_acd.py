#!/usr/bin/env python3
"""
Monkey patch for hutcheb/acd to skip Comments parsing
"""

def patch_acd_library():
    """Patch the acd library to skip Comments parsing"""
    
    # Import the module we need to patch
    import acd.l5x.export_l5x
    import acd.record.comments
    
    # Store original __post_init__
    original_post_init = acd.l5x.export_l5x.ExportL5x.__post_init__
    
    def patched_post_init(self):
        """Patched version that skips Comments parsing"""
        # Call most of the original initialization
        import os
        import sqlite3
        import tempfile
        from sqlite3 import Cursor
        from acd.zip.unzip import Unzip
        from acd.database.dbextract import DbExtract
        from acd.record.comps import CompsRecord
        from acd.record.sbregion import SbRegionRecord
        from acd.record.nameless import NamelessRecord
        from loguru import logger as log
        
        log.info(
            "Creating temporary directory (if it doesn't exist to store ACD database files - "
            + self._temp_dir
        )
        _DEFAULT_SQL_DATABASE_NAME = "acd.db"
        if os.path.exists(os.path.join(self._temp_dir, _DEFAULT_SQL_DATABASE_NAME)):
            os.remove(os.path.join(self._temp_dir, _DEFAULT_SQL_DATABASE_NAME))
        if not os.path.exists(os.path.join(self._temp_dir)):
            os.makedirs(self._temp_dir)
        log.info("Creating sqllite database to store ACD database records")
        self._db = sqlite3.connect(
            os.path.join(self._temp_dir, _DEFAULT_SQL_DATABASE_NAME)
        )
        self._cur: Cursor = self._db.cursor()

        log.debug("Create Comps table in sqllite db")
        self._cur.execute(
            "CREATE TABLE comps(object_id int, parent_id int, comp_name text, seq_number int, record_type int, record BLOB NOT NULL)"
        )
        log.debug("Create pointers table in sqllite db")
        self._cur.execute(
            "CREATE TABLE pointers(object_id int, parent_id int, comp_name text, seq_number int, record_type int, record BLOB NOT NULL)"
        )
        log.debug("Create Rungs table in sqllite db")
        self._cur.execute("CREATE TABLE rungs (unk1 INTEGER, unk2 INTEGER, text TEXT);")
        log.debug("Create Region_map table in sqllite db")
        self._cur.execute(
            "CREATE TABLE region_map (pointer INTEGER PRIMARY KEY, tag_reference INTEGER, record_id INTEGER);"
        )
        log.debug("Create Comments table in sqllite db")
        self._cur.execute(
            "CREATE TABLE comments (pointer INTEGER PRIMARY KEY, comment TEXT);"
        )
        log.debug("Create Nameless table in sqllite db")
        self._cur.execute(
            "CREATE TABLE nameless(object_id int, nameless text, seq_number int)"
        )
        log.info("Extracting ACD database file")
        unzip = Unzip(self.input_filename)
        unzip.write_files(self._temp_dir)

        log.info("Getting records from ACD Comps file and storing in sqllite database")
        comps_db = DbExtract(os.path.join(self._temp_dir, "Comps.Dat")).read()
        for record in comps_db.records.record:
            CompsRecord(self._cur, record)
        self._db.commit()

        log.info("Skipping Region Map parsing due to format issues")

        log.info("Getting records from ACD SbRegion file and storing in sqllite database")
        if os.path.exists(os.path.join(self._temp_dir, "SbRegion.Dat")):
            sb_region_db = DbExtract(os.path.join(self._temp_dir, "SbRegion.Dat")).read()
            for record in sb_region_db.records.record:
                SbRegionRecord(self._cur, record)
            self._db.commit()

        # SKIP COMMENTS PARSING - This is where the Unicode error occurs
        log.info("Skipping Comments parsing due to Unicode issues")
        
        log.info("Getting records from ACD Nameless file and storing in sqllite database")
        if os.path.exists(os.path.join(self._temp_dir, "Nameless.Dat")):
            nameless_db = DbExtract(os.path.join(self._temp_dir, "Nameless.Dat")).read()
            for record in nameless_db.records.record:
                NamelessRecord(self._cur, record)
            self._db.commit()
    
    # Apply the patch
    acd.l5x.export_l5x.ExportL5x.__post_init__ = patched_post_init
    
    print("✅ Patched hutcheb/acd to skip Comments parsing")

if __name__ == "__main__":
    patch_acd_library() 