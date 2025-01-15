import json
import traceback
from typing import List
import time
import humanize
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from langchain_mongodb import MongoDBAtlasVectorSearch
from typing_extensions import Annotated
import uvicorn
import loader
import utils
from eventlogging import EventLogger

load_dotenv()

logger = EventLogger.get_logger()
app = FastAPI()


@app.post("/upload")
async def upload(
    files: Annotated[
        List[UploadFile], File(description="Multiple files upload.")
    ]=[]
    ,json_input_params: str = Form(description="Pass all input pamaraters as a Json string.")):
    inputs = {}
    try:
        inputs = json.loads(json_input_params)
        for key, value in inputs.items():
            print(key," = ",value)

        new_files=utils.UploadFiles(files)
        print(new_files)

        vector_store = utils.MongoDBAtlasVectorSearch_Obj(inputs)

        try:
            documents = loader.LoadFiles(new_files,inputs["userId"])
            MongoDBAtlasVectorSearch.add_documents(vector_store,documents)
        except Exception as e:
            logger.error(e)
            return {"message": "There was an error uploading the file(s)" + str(traceback.TracebackException.from_exception(e).stack.format())}


        WebPagesToIngest = []
        WebPagesToIngest = inputs["WebPagesToIngest"]
        try:
            print(WebPagesToIngest)
            documents = loader.LoadWeb(WebPagesToIngest,inputs["userId"])
            MongoDBAtlasVectorSearch.add_documents(vector_store,documents)
        except Exception as e:
            logger.error(e)
            return {"message": "There was an error uploading the webpage(s)" + str(traceback.TracebackException.from_exception(e).stack.format())}
        msg=[" ".join([file.filename, humanize.naturalsize(file.size)]) for file in files]
        time.sleep(5) # wait for search index build
        return {"message": f"Successfully uploaded {msg}"}
    except Exception as error:
        logger.error(error)
        print(error)
        return {"message": str(traceback.TracebackException.from_exception(error).stack.format())}




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

