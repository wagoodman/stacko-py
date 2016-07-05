import json
import os

class ClassDb(object):

    metadataDir = None
    db = None

    def __init__(self, db=None, metadataDir=None,**kwargs):
        if db:
            self.db = db
        else:
            self.db = {}

        if metadataDir:
            self.metadataDir = metadataDir

    @classmethod
    def from_db(cls, metadataDir, itemCls, key='name',**kwargs):
        db=None
        dbFilename = os.path.join(metadataDir,cls.dbFilename)
        if os.path.exists(dbFilename):
            db = {}
            imageList = json.load(open(dbFilename,'r'))
            for items in imageList:
                db[items[key]] = itemCls(**items)
        obj = cls(db, metadataDir=metadataDir,**kwargs)
        return obj

    def to_db(self):
        jsonDb = []
        for name, obj in list(self.db.items()):
            jsonDb.append(obj.__dict__)

        theFilePath = os.path.join(self.metadataDir,self.dbFilename)
        theFile = open(theFilePath,'w')
        json.dump(jsonDb, theFile)
        theFile.close()
        os.chmod(theFilePath, 0o777)
