import json
import mimetypes
import os
import re

import gradio as gr
import requests
from dotenv import load_dotenv
from gradio import Markdown as m
from langserve import RemoteRunnable
import asyncio
from fastapi import FastAPI
import uvicorn

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

app = FastAPI(
    title="MAAP - MongoDB AI Applications Program",
    version="1.0",
    description="MongoDB AI Applications Program",
)


async def process_request(message, history, userId, dataSource):
    try:
        print(userId, dataSource)
        url = "http://main:8000/rag"
        print(message, history)
        if message and len(message) > 0:
            query = message["text"].strip()
            urls = extract_urls(query)
            print(urls)
            num_files = len(message["files"])
            strTempResponse = ""
            if num_files > 0 or len(urls) > 0:
                strTempResponse = ""
                for i in re.split(
                    r"(\s)",
                    "Initiating upload and content vectorization. \nPlease wait....",
                ):
                    strTempResponse += i
                    await asyncio.sleep(0.025)
                    yield strTempResponse
                    await asyncio.sleep(0.050)

                # Wait for the upload task to complete
                uploadResult = await ingest_data(userId, urls, message["files"])
                if uploadResult:
                    for i in re.split(
                        r"(\s)",
                        "\nFile(s)/URL(s) uploaded  and ingested successfully. \nGiving time for Indexes to Update....",
                    ):
                        strTempResponse += i
                        await asyncio.sleep(0.025)
                        yield strTempResponse
                    await asyncio.sleep(5)
                else:
                    for i in re.split(
                        r"(\s)", "\nFile(s)/URL(s) upload exited with error...."
                    ):
                        strTempResponse += i
                        await asyncio.sleep(0.025)
                        yield strTempResponse

            if len(query) > 0:
                prompt = json.dumps(
                    {"query": query, "userId": userId, "dataSource": dataSource}
                )
                strResponse = ""
                llm = RemoteRunnable(url)
                async for msg in llm.astream(prompt):
                    if isinstance(msg, str):
                        strResponse += msg
                    elif hasattr(msg, "content"):
                        strResponse += msg.content
                    else:
                        raise TypeError(f"Unexpected message type: {type(msg)}")
                    yield strResponse
                try:
                    response_dict = json.loads(strResponse)
                    yield (
                        response_dict.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                except json.JSONDecodeError:
                    pass
            else:
                yield "Hi, how may I help you?"
        else:
            yield "Hi, how may I help you?"
    except Exception as error:
        print(error)
        yield "There was an error.\n" + str(error)


def extract_urls(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    return [x[0] for x in url]


async def ingest_data(userId, urls, new_files):
    url = "http://loader:8001/upload"

    inputs = {
        "userId": userId,
        "MongoDB_URI": MONGODB_URI,
        "MongoDB_text_key": "document_text",
        "MongoDB_embedding_key": "document_embedding",
        "MongoDB_index_name": "document_vector_index",
        "MongoDB_database_name": "maap_data_loader",
        "MongoDB_collection_name": "document",
        "WebPagesToIngest": urls,
    }

    payload = {"json_input_params": json.dumps(inputs)}
    files = []

    for file in new_files:
        file_name, file_ext = os.path.splitext(file)
        file_name = os.path.basename(file)
        mime_type, encoding = mimetypes.guess_type(file)
        file_types = [
            ".bmp",
            ".csv",
            ".doc",
            ".docx",
            ".eml",
            ".epub",
            ".heic",
            ".html",
            ".jpeg",
            ".png",
            ".md",
            ".msg",
            ".odt",
            ".org",
            ".p7s",
            ".pdf",
            ".png",
            ".ppt",
            ".pptx",
            ".rst",
            ".rtf",
            ".tiff",
            ".txt",
            ".tsv",
            ".xls",
            ".xlsx",
            ".xml",
            ".vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".vnd.openxmlformats-officedocument.presentationml.presentation",
        ]
        if file_ext in file_types:
            files.append(("files", (file_name, open(file, "rb"), mime_type)))
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)

    print(response.text)
    if "Successfully uploaded" in response.text:
        return True
    else:
        return False


def print_like_dislike(x: gr.LikeData):
    print(x.index, x.value, x.liked)
    return


head = """
<link rel="shortcut icon" href="https://ok5static.oktacdn.com/bc/image/fileStoreRecord?id=fs0jq9i9e0E4EFpjn297" type="image/x-icon">
"""
mdblogo_svg = "https://ok5static.oktacdn.com/fs/bco/1/fs0jq9i9coLeryBSy297"


PLUS = """data:image/png;base64,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EnD+NQDf7vubfp8AAQIECBCoFzg+7v92cpRPJ697lQABAgQIELg8geNj/fYUwPrU/1+Xd04nIkCAAAECBE4Efj+8fv1FgdtnAHxHvxMdrxIgQIAAgQsWuH7M354L8Nz/BSftaAQIECBA4Ezgan0GYH363wsBAgQIECAwR+D9+hqA/x9+rOcEvBAgQIAAAQIzBP63fQ3AjOM6JQECBAgQIHAtsL4GwPP/LgMBAgQIEBgm4DMAwwJ3XAIECBAgsAQUAPeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAQAFwBwgQIECAwEABBWBg6I5MgAABAgQUAHeAAAECBAgMFFAABobuyAQIECBAYBWAzxgIECBAgACB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"""


custom_css = """
           
            .message-row img {
                margin: 0px !important;
            }

            .avatar-container img {
            padding: 0px !important;
            }

            footer {visibility: hidden}; 
        """

with gr.Blocks(
    head=head,
    fill_height=True,
    fill_width=True,
    css=custom_css,
    title="MongoDB AI Applications Program (MAAP)",
    theme=gr.themes.Soft(primary_hue=gr.themes.colors.green),
) as demo:
    with gr.Row():
        m(
            f"""
<center>
    <div style="display: flex; justify-content: center; align-items: center;">
        <a href="https://www.mongodb.com/">
            <img src="{mdblogo_svg}" width="200px" style="margin-right: 20px"/>
        </a>
    <img src="{PLUS}" width="30px" style="margin: 10px 20px 0 5px;" />
    <a href="https://www.arcee.ai" style="display: flex; align-items: center; margin: 0px 20px 15px 0px;">
        <img src="https://cdn.prod.website-files.com/667c389208d8cc3b4b68472a/667c389208d8cc3b4b684903_Logo.png" 
             alt="Arcee Logo" class="navbar-logo-icon" style="margin-right: 5px;" />
        <svg xmlns="http://www.w3.org/2000/svg" width="144px" height="27px" viewBox="0 0 144 27" fill="none" class="navbar-logo-text"><path d="M21.2069 7.49038V25.9048H18.0439L17.6601 23.6643C15.9298 25.3511 13.5167 26.3617 10.7301 26.3617C5.04005 26.3617 0.78125 22.2163 0.78125 16.6962C0.78125 11.1761 5.0371 7.05321 10.7301 7.05321C13.5488 7.05321 15.9824 8.07797 17.72 9.79431L18.181 7.49179L21.2069 7.49038ZM17.2677 16.6948C17.2677 13.2256 14.6415 10.6504 11.0335 10.6504C7.42554 10.6504 4.7673 13.2509 4.7673 16.6948C4.7673 20.1388 7.42693 22.7392 11.0276 22.7392C14.6283 22.7392 17.2677 20.1641 17.2677 16.6948ZM80.3271 17.9936H64.8125C65.3042 20.9779 67.5349 22.8124 70.6644 22.8124C72.9463 22.8124 74.7962 21.7933 75.8044 20.1148H79.9391C78.4189 24.003 74.9291 26.3604 70.6644 26.3604C65.0765 26.3604 60.8455 22.2036 60.8455 16.7061C60.8455 11.2084 65.0663 7.05181 70.6644 7.05181C76.5119 7.05181 80.406 11.3912 80.406 16.7511C80.4006 17.1664 80.3729 17.5811 80.3227 17.9936H80.3271ZM64.9117 14.918H76.4668C75.762 12.1207 73.5737 10.4648 70.6644 10.4648C67.7086 10.4648 65.5551 12.1854 64.9117 14.918ZM102.664 17.9936H87.1492C87.6409 20.9779 89.8718 22.8124 92.9997 22.8124C95.2816 22.8124 97.1315 21.7933 98.1411 20.1148H102.276C100.754 24.003 97.2658 26.3604 92.9997 26.3604C87.4135 26.3604 83.1824 22.2036 83.1824 16.7061C83.1824 11.2084 87.4017 7.05181 92.9997 7.05181C98.8487 7.05181 102.741 11.3912 102.741 16.7511C102.739 17.1664 102.713 17.5811 102.664 17.9936ZM87.2485 14.918H98.802C98.0974 12.1207 95.9104 10.4648 92.9997 10.4648C90.0439 10.4648 87.8904 12.1854 87.2485 14.918ZM134.051 7.49038V25.9048H130.882L130.503 23.6643C128.771 25.3511 126.356 26.3617 123.571 26.3617C117.881 26.3617 113.622 22.2163 113.622 16.6962C113.622 11.1761 117.88 7.05321 123.571 7.05321C126.387 7.05321 128.823 8.07797 130.562 9.79431L131.02 7.49179L134.051 7.49038ZM130.112 16.6948C130.112 13.2256 127.477 10.6504 123.876 10.6504C120.275 10.6504 117.615 13.2453 117.615 16.6948C117.615 20.1444 120.274 22.7392 123.876 22.7392C127.478 22.7392 130.116 20.1641 130.116 16.6948H130.112ZM139.658 7.50164H143.586V25.9162H139.663L139.658 7.50164ZM110.528 23.7373C110.528 23.2924 110.391 22.8577 110.134 22.4879C109.878 22.118 109.513 21.8297 109.087 21.6594C108.66 21.4891 108.191 21.4446 107.738 21.5315C107.285 21.6183 106.869 21.8324 106.543 22.1469C106.216 22.4615 105.994 22.8623 105.904 23.2985C105.814 23.7349 105.86 24.187 106.037 24.598C106.214 25.009 106.513 25.3603 106.897 25.6074C107.28 25.8546 107.732 25.9864 108.194 25.9864C108.5 25.9869 108.804 25.9292 109.088 25.8165C109.372 25.7037 109.63 25.538 109.847 25.3291C110.064 25.1203 110.237 24.8721 110.354 24.5991C110.472 24.3258 110.532 24.033 110.532 23.7373H110.528ZM143.966 2.8741C143.966 2.42927 143.829 1.99443 143.572 1.62457C143.316 1.25471 142.951 0.966432 142.525 0.796202C142.098 0.625974 141.629 0.581435 141.176 0.668217C140.724 0.754999 140.307 0.969205 139.981 1.28375C139.655 1.5983 139.433 1.99904 139.342 2.43533C139.252 2.87162 139.297 3.32383 139.474 3.7348C139.651 4.14576 139.951 4.49703 140.335 4.74417C140.718 4.99129 141.169 5.12321 141.631 5.12321C142.25 5.12321 142.844 4.88624 143.283 4.46446C143.72 4.04268 143.966 3.47059 143.966 2.8741Z" fill="currentColor"></path><path d="M37.7127 7.40439V10.9791H35.6336C32.3859 10.9791 30.7635 12.7643 30.7635 16.1V25.9174H26.8359V7.50279H29.4928L30.158 10.0134C31.525 8.26889 33.3999 7.39877 36.0085 7.39877L37.7127 7.40439ZM38.852 16.6932C38.852 11.1927 43.1632 7.05859 48.8781 7.05859C53.6008 7.05859 57.289 9.84608 58.3512 14.0702H54.4543C53.449 11.9518 51.354 10.6698 48.8619 10.6698C45.4233 10.6698 42.8468 13.29 42.8468 16.7016C42.8468 20.1133 45.4568 22.7531 48.8619 22.7531C51.3626 22.7531 53.3848 21.4529 54.4295 19.2122H58.3935C57.3415 23.5164 53.5788 26.3672 48.8619 26.3672C43.1705 26.3672 38.8477 22.1923 38.8477 16.6932H38.852Z" fill="currentColor" class="path-2"></path>
        </svg>
    </a>
    </div>
    <h1>MongoDB AI Applications Program (<a href="https://www.mongodb.com/services/consulting/ai-applications-program">MAAP</a>)</h1>
    <h3>An integrated end-to-end technology stack in the form of MAAP Framework.</h3>
</center>
"""
        )

    with gr.Accordion(label="--- Inputs ---", open=True) as AdditionalInputs:
        m(
            """<p color="#00684a">Provide a User Id to store and retrieve User specific file(s) data from MongoDB.<br/>Select the relevant MongoDB Atlas Datasource(s) for Vector Search.<br/>Upload the file(s) using the Attach(clip) button or type in URL(s) to get the information extracted from them and stored in MongoDB Atlas Vector Database for performing Contextually-Relevant Searches.</p>"""
        )
        txtUserId = gr.Textbox(
            value="your.email@yourdomain.com", label="User Id", key="UserId"
        )
        chbkgDS = gr.CheckboxGroup(
            choices=["Trip Recommendations", "User Uploaded Data"],
            value=["Trip Recommendations", "User Uploaded Data"],
            label="MongoDB Datasources",
            info="Which collections to look for relevant information?",
            key="db",
        )

    txtChatInput = gr.MultimodalTextbox(
        interactive=True,
        file_count="multiple",
        placeholder="Type your query and/or upload file(s) and interact with it...",
        label="User Query",
        show_label=True,
        render=False,
    )

    examples = [
        [
            "Recommend places to visit in India.",
            "your.email@yourdomain.com",
            ["Trip Recommendations"],
        ],
        [
            "Explain https://www.mongodb.com/services/consulting/ai-applications-program",
            "your.email@yourdomain.com",
            ["User Uploaded Data"],
        ],
    ]

    bot = gr.Chatbot(
        elem_id="chatbot",
        bubble_full_width=True,
        type="messages",
        autoscroll=True,
        avatar_images=[
            "https://ca.slack-edge.com/E01C4Q4H3CL-U04D0GXU2B1-g1a101208f57-192",
            "https://avatars.slack-edge.com/2021-11-01/2659084361479_b7c132367d18b6b7ffa0_512.png",
        ],
        show_copy_button=True,
        render=False,
        min_height="450px",
        label="Type your query and/or upload file(s) and interact with it...",
    )
    bot.like(print_like_dislike, None, None, like_user_message=False)

    CI = gr.ChatInterface(
        fn=process_request,
        chatbot=bot,
        type="messages",
        title="",
        description="",
        multimodal=True,
        additional_inputs=[txtUserId, chbkgDS],
        additional_inputs_accordion=AdditionalInputs,
        textbox=txtChatInput,
        fill_height=True,
        show_progress=False,
        concurrency_limit=None,
    )

    gr.Examples(
        examples,
        inputs=[
            txtChatInput,
            txtUserId,
            chbkgDS,
        ],
        examples_per_page=2,
    )

    with gr.Row():
        m(
            """
            <center><a href="https://www.mongodb.com/">MongoDB</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <a href="https://www.arcee.ai/product/supernova">Arcee SuperNova</a>
            </center>
       """
        )


if __name__ == "__main__":
    app = gr.mount_gradio_app(
        app, demo, path="/", server_name="0.0.0.0", server_port=7860
    )
    uvicorn.run(app, host="0.0.0.0", port=7860)
