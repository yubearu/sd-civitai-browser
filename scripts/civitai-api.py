import requests
from PIL import Image
from io import BytesIO
from fake_useragent import UserAgent as ua
import json
import modules.scripts as scripts
import gradio as gr
from modules import script_callbacks
import time
import threading
import urllib.request
import urllib.error
import os
from tqdm import tqdm
import re
from requests.exceptions import ConnectionError
import urllib.request

PLACEHOLDER = "<no select>"

def download_file(url, file_name):
    # Maximum number of retries
    max_retries = 5

    # Delay between retries (in seconds)
    retry_delay = 10

    while True:
        # Check if the file has already been partially downloaded
        if os.path.exists(file_name):
            # Get the size of the downloaded file
            downloaded_size = os.path.getsize(file_name)

            # Set the range of the request to start from the current
            # size of the downloaded file
            headers = {"Range": f"bytes={downloaded_size}-"}
        else:
            downloaded_size = 0
            headers = {}

        # Split filename from included path
        tokens = re.split(re.escape('\\'), file_name)
        file_name_display = tokens[-1]

        # Initialize the progress bar
        progress = tqdm(total=1000000000, unit="B", unit_scale=True,
                        desc=f"Downloading {file_name_display}",
                        initial=downloaded_size, leave=False)

        # Open a local file to save the download
        with open(file_name, "ab") as f:
            while True:
                try:
                    # Send a GET request to the URL and save the response to the local file
                    response = requests.get(url, headers=headers, stream=True)

                    # Get the total size of the file
                    total_size = int(response.headers.get("Content-Length", 0))

                    # Update the total size of the progress bar if the `Content-Length` header is present
                    if total_size == 0:
                        total_size = downloaded_size
                    progress.total = total_size

                    # Write the response to the local file and update the progress bar
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            progress.update(len(chunk))

                    downloaded_size = os.path.getsize(file_name)
                    # Break out of the loop if the download is successful
                    break
                except ConnectionError as e:
                    # Decrement the number of retries
                    max_retries -= 1

                    # If there are no more retries, raise the exception
                    if max_retries == 0:
                        raise e

                    # Wait for the specified delay before retrying
                    time.sleep(retry_delay)

        # Close the progress bar
        progress.close()
        downloaded_size = os.path.getsize(file_name)
        # Check if the download was successful
        if downloaded_size >= total_size:
            print(f"{file_name_display} successfully downloaded.")
            break
        else:
            print(f"Error: File download failed. Retrying... {file_name_display}")

def make_new_folder(content_type, use_new_folder, model_name, lora_old):
    if content_type == "Checkpoint":
        folder = "models/Stable-diffusion"
        new_folder = "models/Stable-diffusion/new"
    elif content_type == "Hypernetwork":
        folder = "models/hypernetworks"
        new_folder = "models/hypernetworks/new"
    elif content_type == "TextualInversion":
        folder = "embeddings"
        new_folder = "embeddings/new"
    elif content_type == "AestheticGradient":
        folder = "extensions/stable-diffusion-webui-aesthetic-gradients/aesthetic_embeddings"
        new_folder = "extensions/stable-diffusion-webui-aesthetic-gradients/aesthetic_embeddings/new"
    elif content_type == "VAE":
        folder = "models/VAE"
        new_folder = "models/VAE/new"
    elif content_type == "LORA":
        if lora_old:
            folder = "extensions/sd-webui-additional-networks/models/lora"
            new_folder = "extensions/sd-webui-additional-networks/models/lora/new"
        else:
            folder = "models/Lora"
            new_folder = "models/Lora/new"
    elif content_type == "LoCon":
        if lora_old:
            folder = "extensions/sd-webui-additional-networks/models/LyCORIS"
            new_folder = "extensions/sd-webui-additional-networks/models/LyCORIS/new"
        else:
            folder = "models/LyCORIS"
            new_folder = "models/LyCORIS/new"
    if content_type == "TextualInversion" or content_type == "VAE" or \
            content_type == "AestheticGradient":
        if use_new_folder:
            model_folder = new_folder
            if not os.path.exists(new_folder):
                os.makedirs(new_folder)

        else:
            model_folder = folder
            if not os.path.exists(model_folder):
                os.makedirs(model_folder)
    else:
        if use_new_folder:
            model_folder = os.path.join(new_folder,model_name.replace(" ","_").replace("(","").replace(")","").replace("|","").replace(":","-"))
            if not os.path.exists(new_folder):
                os.makedirs(new_folder)
            if not os.path.exists(model_folder):
                os.makedirs(model_folder)

        else:
            model_folder = os.path.join(folder,model_name.replace(" ","_").replace("(","").replace(")","").replace("|","").replace(":","-"))
            if not os.path.exists(model_folder):
                os.makedirs(model_folder)
    return model_folder

def download_file_thread(url, file_name, content_type, use_new_folder, model_name, lora_old):
    model_folder = make_new_folder(content_type, use_new_folder, model_name, lora_old)

    path_to_new_file = os.path.join(model_folder, file_name)

    thread = threading.Thread(target=download_file, args=(url, path_to_new_file))

        # Start the thread
    thread.start()

def save_text_file(file_name, content_type, use_new_folder, trained_words, model_name, lora_old):
    model_folder = make_new_folder(content_type, use_new_folder, model_name, lora_old)

    path_to_new_file = os.path.join(model_folder, file_name.replace(".ckpt",".txt").replace(".safetensors",".txt").replace(".pt",".txt").replace(".yaml",".txt"))
    if not os.path.exists(path_to_new_file):
        with open(path_to_new_file, 'w') as f:
            f.write(trained_words)
    if os.path.getsize(path_to_new_file) == 0:
        print("Current model doesn't have any trained tags")
    else:
        print("Trained tags saved as text file")

# Set the URL for the API endpoint
api_url = "https://civitai.com/api/v1/models?limit=50"
json_data = None

def api_to_data(content_type, sort_type, use_search_term, search_term=None):
    if use_search_term and search_term:
        search_term = search_term.replace(" ","%20")
        return request_civit_api(f"{api_url}&types={content_type}&sort={sort_type}&query={search_term}")
    else:
        return request_civit_api(f"{api_url}&types={content_type}&sort={sort_type}")

def api_next_page(next_page_url=None):
    global json_data
    try: json_data['metadata']['nextPage']
    except: return
    if json_data['metadata']['nextPage'] is not None:
        next_page_url = json_data['metadata']['nextPage']
    if next_page_url is not None:
        return request_civit_api(next_page_url)

def update_next_page(show_nsfw):
    global json_data
    json_data = api_next_page()
    model_dict = {}
    try: json_data['items']
    except TypeError: return gr.Dropdown.update(choices=[], value=None)
    if show_nsfw:
        for item in json_data['items']:
            model_dict[item['name']] = item['name']
    else:
        for item in json_data['items']:
            temp_nsfw = item['nsfw']
            if not temp_nsfw:
                model_dict[item['name']] = item['name']
    return gr.Dropdown.update(choices=[PLACEHOLDER] + [v for k, v in model_dict.items()], value=PLACEHOLDER), gr.Dropdown.update(choices=[], value=None)


def update_model_list(content_type, sort_type, use_search_term, search_term, show_nsfw):
    global json_data
    json_data = api_to_data(content_type, sort_type, use_search_term, search_term)
    model_dict = {}
    if show_nsfw:
        for item in json_data['items']:
            model_dict[item['name']] = item['name']
    else:
        for item in json_data['items']:
            temp_nsfw = item['nsfw']
            if not temp_nsfw:
                model_dict[item['name']] = item['name']
    return gr.Dropdown.update(choices=[PLACEHOLDER] + [v for k, v in model_dict.items()], value=PLACEHOLDER), gr.Dropdown.update(choices=[], value=None)

def update_model_versions(model_name=None):
    if model_name is not None and model_name != PLACEHOLDER:
        global json_data
        versions_dict = {}
        for item in json_data['items']:
            if item['name'] == model_name:

                for model in item['modelVersions']:
                    versions_dict[model['name']] = item["name"]
        return gr.Dropdown.update(choices=[PLACEHOLDER] + [k + ' - ' + v for k, v in versions_dict.items()], value=PLACEHOLDER)
    else:
        return gr.Dropdown.update(choices=[], value=None)

def update_dl_url(model_name=None, model_version=None, model_filename=None):
    if model_filename:
        global json_data
        dl_dict = {}
        dl_url = None
        model_version = model_version.replace(f' - {model_name}','').strip()
        for item in json_data['items']:
            if item['name'] == model_name:
                for model in item['modelVersions']:
                    if model['name'] == model_version:
                        for file in model['files']:
                            if file['name'] == model_filename:
                                dl_url = file['downloadUrl']
        return gr.Textbox.update(value=dl_url)
    else:
        return gr.Textbox.update(value=None)

def update_model_info(model_name=None, model_version=None):
    if model_name and model_version and model_name != PLACEHOLDER and model_version != PLACEHOLDER:
        model_version = model_version.replace(f' - {model_name}','').strip()
        global json_data
        output_html = ""
        output_training = ""
        img_html = ""
        model_desc = ""
        dl_dict = {}
        for item in json_data['items']:
            if item['name'] == model_name:
                model_uploader = item['creator']['username']
                if item['description']:
                    model_desc = item['description']
                for model in item['modelVersions']:
                    if model['name'] == model_version:
                        if model['trainedWords']:
                            output_training = ", ".join(model['trainedWords'])

                        for file in model['files']:
                            dl_dict[file['name']] = file['downloadUrl']

                        model_url = model['downloadUrl']
                        #model_filename = model['files']['name']

                        img_html = '<HEAD><style>img { display: inline-block; }</style></HEAD><div class="column">'
                        for pic in model['images']:
                            img_html = img_html + f'<img src={pic["url"]} width=400px></img>'
                        img_html = img_html + '</div>'
                        output_html = f"<p><b>Model:</b> {model_name}<br><b>Version:</b> {model_version}<br><b>Uploaded by:</b> {model_uploader}<br><br><a href={model_url}><b>Download Here</b></a></p><br><br>{model_desc}<br><div align=center>{img_html}</div>"

        return gr.HTML.update(value=output_html), gr.Textbox.update(value=output_training), gr.Dropdown.update(choices=[PLACEHOLDER] + [k for k, v in dl_dict.items()], value=PLACEHOLDER)
    else:
        return gr.HTML.update(value=None), gr.Textbox.update(value=None), gr.Dropdown.update(choices=[], value=None)


def request_civit_api(api_url=None):
    # Make a GET request to the API
    response = requests.get(api_url)

    # Check the status code of the response
    if response.status_code != 200:
      print("Request failed with status code: {}".format(response.status_code))
      exit()

    data = json.loads(response.text)
    return data

#from https://github.com/thetrebor/sd-civitai-browser/blob/add-download-images/scripts/civitai-api.py
def update_everything(list_models, list_versions, model_filename, dl_url):
    (a, d, f) = update_model_info(list_models, list_versions)
    dl_url = update_dl_url(list_models, list_versions, f['value'])
    return (a, d, f, list_versions, list_models, dl_url)

def save_image_files(preview_image_html, model_filename, content_type, use_new_folder, list_models, lora_old):
    print("Save Images Clicked")
    model_folder = make_new_folder(content_type, use_new_folder, list_models, lora_old)

    img_urls = re.findall(r'src=[\'"]?([^\'" >]+)', preview_image_html)

    name = os.path.splitext(model_filename)[0]
    assert(name != "<no select>"), "Please select a Model Filename to download"
    current_directory = os.getcwd()
    while os.path.basename(current_directory) != "stable-diffusion-webui":
        current_directory = os.path.dirname(current_directory)
    new_model_folder = os.path.join(current_directory, model_folder)
    # new_model_folder = os.path.join(current_directory,list_models.replace(" ","_").replace("(","").replace(")","").replace("|","").replace(":","-"))

    headers = {"User-Agent": str(ua.random)}
    print(img_urls)

    for i, img_url in enumerate(img_urls):
        filename = f'{name}_{i}.png'
        # img_url = img_url.replace("https", "http").replace("=","%3D")

        print(f'Downloading {img_url} to {filename}')
        try:
            with requests.get(img_url, headers) as url:
                with open(os.path.join(new_model_folder, filename), 'wb') as f:
                    with Image.open(BytesIO(url.content)) as save_me:
                        save_me.save(f)
                        print(f'Downloaded {img_url}')
            # with urllib.request.urlretrieve(img_url, os.path.join(model_folder, filename)) as dl:

        except urllib.error.URLError as e:
            print(f'Error: {e.reason}')

        finally:
            print("Images downloaded.")

    if os.path.exists(os.path.join(new_model_folder, f'{name}_0.png')):
        with open(os.path.join(new_model_folder, f'{name}_0.png'), 'rb') as f_in:
            with open(os.path.join(new_model_folder, f'{name}.png'), 'wb') as f_out:
                f_out.write(f_in.read())

def on_ui_tabs():
    with gr.Blocks() as civitai_interface:
        with gr.Row():
            with gr.Column(scale=2):
                content_type = gr.Radio(label='Content type:', choices=["Checkpoint","Hypernetwork","TextualInversion","AestheticGradient", "VAE", "LORA", "LoCon"], value="Checkpoint", type="value")
            with gr.Column(scale=2):
                sort_type = gr.Radio(label='Sort List by:', choices=["Newest","Most Downloaded","Highest Rated","Most Liked"], value="Newest", type="value")
            with gr.Column(scale=1):
                show_nsfw = gr.Checkbox(label="Show NSFW", value=True)
        with gr.Row():
            use_search_term = gr.Checkbox(label="Search by term?", value=True)
            search_term = gr.Textbox(label="Search Term", interactive=True, lines=1)
        with gr.Row():
            get_list_from_api = gr.Button(label="Get List", value="Get List")
            get_next_page = gr.Button(value="Next Page")
        with gr.Row():
            list_models = gr.Dropdown(label="Model", choices=[], interactive=True, elem_id="quicksettings", value=None)
            list_versions = gr.Dropdown(label="Version", choices=[], interactive=True, elem_id="quicksettings", value=None)
        with gr.Row():
            txt_list = ""
            dummy = gr.Textbox(label='Trained Tags (if any)', value=f'{txt_list}', interactive=True, lines=1)
            model_filename = gr.Dropdown(label="Model Filename", choices=[], interactive=True, value=None)
            dl_url = gr.Textbox(label="Download Url", interactive=False, value=None)
        with gr.Row():
            update_info = gr.Button(value='1st - Get Model Info')
            save_text = gr.Button(value="2nd - Save Trained Tags as Text")
            save_images = gr.Button(value="3rd - Save Images")
            download_model = gr.Button(value="4th - Download Model")
            with gr.Row():
                save_model_in_new = gr.Checkbox(label="Save Model to new folder", value=False)
                old_lora = gr.Checkbox(label="Save LoRA to additional-networks", value=False)
        with gr.Row():
            preview_image_html = gr.HTML()
        save_text.click(
            fn=save_text_file,
            inputs=[
            model_filename,
            content_type,
            save_model_in_new,
            dummy,
            list_models,
            old_lora,
            ],
            outputs=[]
        )
        save_images.click(
            fn=save_image_files,
            inputs=[
            preview_image_html,
            model_filename,
            content_type,
            save_model_in_new,
            list_models,
            old_lora,
            ],
            outputs=[]
        )
        download_model.click(
            fn=download_file_thread,
            inputs=[
            dl_url,
            model_filename,
            content_type,
            save_model_in_new,
            list_models,
            old_lora,
            ],
            outputs=[]
        )
        get_list_from_api.click(
            fn=update_model_list,
            inputs=[
            content_type,
            sort_type,
            use_search_term,
            search_term,
            show_nsfw,
            ],
            outputs=[
            list_models,
            list_versions,
            ]
        )
        update_info.click(
            fn=update_everything,
            #fn=update_model_info,
            inputs=[
            list_models,
            list_versions,
            model_filename,
            dl_url
            ],
            outputs=[
            preview_image_html,
            dummy,
            model_filename,
            list_versions,
            list_models,
            dl_url
            ]
        )
        list_models.change(
            fn=update_model_versions,
            inputs=[
            list_models,
            ],
            outputs=[
            list_versions,
            ]
        )

        list_versions.change(
            fn=update_model_info,
            inputs=[
            list_models,
            list_versions,
            ],
            outputs=[
            preview_image_html,
            dummy,
            model_filename,
            ]
        )
        model_filename.change(
            fn=update_dl_url,
            inputs=[list_models, list_versions, model_filename,],
            outputs=[dl_url,]
        )
        get_next_page.click(
            fn=update_next_page,
            inputs=[
            show_nsfw,
            ],
            outputs=[
            list_models,
            list_versions,
            ]
        )

    return (civitai_interface, "CivitAi", "civitai_interface"),

script_callbacks.on_ui_tabs(on_ui_tabs)
