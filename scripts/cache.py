import base64
from io import BytesIO
import os
import re
import redis
import json
import modules.scripts as scripts
from modules.shared import opts
import gradio as gr

redis_save_env = bool(os.environ.get('REDIS_SAVE', False) == 'True')
redis_host_env = os.environ.get('REDIS_HOST', '127.0.0.1')
redis_port_env = int(os.environ.get('REDIS_PORT', 6379))
redis_db_env = int(os.environ.get('REDIS_DB', 0))
redis_auth_env = os.environ.get('REDIS_AUTH', '')
redis_prefix_env = os.environ.get('REDIS_PREFIX', '')


def get_collection(host: str = '127.0.0.1', port: int = 6379, db: int = 0, password: str = ''):
    conn_pool = redis.ConnectionPool(host=host, port=port, db=db, password=password, max_connections=10)
    return redis.Redis(connection_pool=conn_pool)


class Scripts(scripts.Script):
    def title(self):
        return "Redis Storage"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        import modules.ui
        print(f"--------------------------")
        print(f"Redis Configure")
        print(f"--------------------------")
        print(f"save: {redis_save_env}")
        print(f"host=>{redis_host_env}")
        print(f"port=>{redis_port_env}")
        print(f"db=>{redis_db_env}")
        print(f"auth=>{redis_auth_env}")
        print(f"prefix=>{redis_prefix_env}")
        print(f"--------------------------")

        with gr.Group():
            with gr.Accordion("Redis Configure", open=True):
                with gr.Row():
                    _save = gr.Checkbox(label="enable", value=bool(redis_save_env))
                with gr.Group():
                    with gr.Row():
                        _host = gr.Textbox(label="host", value=str(redis_host_env))
                        _port = gr.Textbox(label="port", value=str(redis_port_env))
                        _db = gr.Textbox(label="database", value=str(redis_db_env))
                        _auth = gr.Textbox(label="auth", value=str(redis_auth_env))
                    with gr.Row():
                        _prefix = gr.Textbox(label="key path prefix", info="redis key path prefix, e.g: MM:NN:", value=str(redis_prefix_env))
        return [_save, _host, _port, _db, _auth, _prefix]

    def postprocess(self, p, processed, save, host, port, db, auth, prefix):
        collection = get_collection(host, port, db, auth) if save else None
        if collection is None:
            return True

        # print(f"------------>samples_format[{opts.samples_format}]")
        # print(f"------------>images[{len(processed.images)}].seeds[{len(processed.all_seeds)}].subseeds[{len(processed.all_subseeds)}]")
        # print(f"------------>info[{processed.info}]")
        # print(f"------------>infotexts[{processed.infotexts}]")

        # opts.return_grid==true
        if len(processed.images) == len(processed.all_seeds) + 1:
            processed.images = processed.images[1:len(processed.images)]
            processed.infotexts = processed.infotexts[1:len(processed.infotexts)]

        for i in range(len(processed.images)):
            image = processed.images[i]
            buffer = BytesIO()
            image.save(buffer, "png")
            image_bytes = buffer.getvalue()
            # base64_image = base64.b64encode(image_bytes).decode('ascii')
            seed = processed.all_seeds[i]
            # subseed = processed.all_subseeds[i]
            info = processed.infotexts[i]
            path = processed.path[i]

            # Usage:
            # Settings -> Saving images/grids -> Images filename pattern -> [datetime<%Y%m%d_%H%M%S>]_[seed]_[model_hash]
            # Unclick all checkbox,Only click following checkbox:
            # 'Always save all generated images'
            # 'Do not save grids consisting of one picture'
            # 'Save text information about generation parameters as chunks to png files'
            # 'If the saved image file size is above the limit, or its either width or height are above the limit, save a downscaled copy as JPG'
            # 'Use original name for output filename during batch process in extras tab'
            # 'When using 'Save' button, only save a single selected image'

            # Settings -> Saving to a directory -> Directory name pattern -> [date]
            # Unclick all checkbox,Only click following checkbox:
            # 'Save images to a subdirectory'

            # outputs/txt2img-images/2023-06-02/20230602_061753_2114655488_fc2511737a.jpg
            arr = path.split("/")
            if len(arr) != 4:
                print(f"not enough delimiters[/][{len(arr)}]")
                return True

            # outputs/txt2img-images
            frontkey = ':'.join(arr[:len(arr) - 2])

            # 20230602_061753_2114655488_fc2511737a.jpg
            lastarr = ''.join(arr[len(arr) - 1:]).split(".")[0].split("_")
            if len(lastarr) != 4:
                print(f"not enough delimiters[_][{len(lastarr)}]")
                return True

            year = lastarr[0][0:4]
            month = lastarr[0][4:6]
            day = lastarr[0][6:8]

            hour = lastarr[1][0:2]
            minute = lastarr[1][2:4]
            # second = lastarr[1][4:6]

            seed = lastarr[2]
            mdlhash = lastarr[3]

            endkey = '{}:{}:{}:{}:{}:{}:{}'.format(year, month, day, hour, minute, mdlhash, seed)

            realkey = str(prefix) + frontkey + ":" + endkey

            print(f"image[{i}].realkey[{realkey}].seeds[{seed}].bytes_size[{len(image_bytes)}].head[{image_bytes[:16].hex(' ')}].tail[{image_bytes[len(image_bytes) - 20:len(image_bytes) - 12].hex(' ')}]")
            # collection.hmset("RS:B:100:image", {"image": base64_image})
            # collection.hmset("RS:B:100:image:" + str(i), {str(seed): image_bytes})
            if processed.mdl is None:
                collection.hmset(realkey, {"m": "", "p": info, "u": path})
            else:
                collection.hmset(realkey, {"m": processed.mdl, "p": info, "u": path})

        # full = processed.js()
        # # print(f"postprocess --------------")
        # # print(f"processed => {full}")
        # # print(f"--------------------------")
        # regex = r"Steps:.*$"
        # info = re.findall(regex, processed.info, re.M)[0]
        # input_dict = dict(item.split(": ") for item in str(info).split(", "))
        # # collection.hmset("RS:B:100:info", {"full": full, "info": info, "json": json.dumps(input_dict)})
        # collection.hmset(str(prefix) + str(processed.seed), {"info": full, "json": json.dumps(input_dict)})

        print(f"postprocess ---> Save2Redis.completed!")
        return True
