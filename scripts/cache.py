import base64
from io import BytesIO
import os
import re
import redis
import json
import modules.scripts as scripts
import gradio as gr

redis_save = bool(os.environ.get('REDIS_SAVE', False) == 'True')
redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_db = int(os.environ.get('REDIS_DB', 0))
redis_auth = os.environ.get('REDIS_AUTH', '')
redis_prefix = os.environ.get('REDIS_PREFIX', '')

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
        print(f"Redis Configure save: {redis_save}")
        print(f"redis_host=>{redis_host}")
        print(f"redis_port=>{redis_port}")
        print(f"redis_db=>{redis_db}")
        print(f"redis_auth=>{redis_auth}")
        print(f"redis_prefix=>{redis_prefix}")

        with gr.Group():
            with gr.Accordion("Redis Configure", open=True):
                with gr.Row():
                    checkbox_save_to_redis = gr.Checkbox(label="enable", value=bool(redis_save))
                with gr.Group():
                    with gr.Row():
                        host = gr.Textbox(label="redis_host", value=str(redis_host))
                        port = gr.Textbox(label="redis_port", value=str(redis_port))
                        db = gr.Textbox(label="redis_db", value=str(redis_db))
                        pwd = gr.Textbox(label="redis_auth", value=str(redis_auth))
                    with gr.Row():
                        prefix = gr.Textbox(label="redis_prefix", value=str(redis_prefix))
        return [checkbox_save_to_redis, host, port, db, pwd, prefix]

    def postprocess(self, p, processed, checkbox_save_to_redis, host, port, db, pwd, prefix):
        print(f"------------>checkbox_save_to_redis[{checkbox_save_to_redis}]")
        print(f"------------>host[{host}]")
        print(f"------------>port[{port}]")
        print(f"------------>db[{db}]")
        print(f"------------>pwd[{pwd}]")
        print(f"------------>prefix[{prefix}]")
        collection = get_collection(host, port, db, pwd) if checkbox_save_to_redis else None
        if collection is None:
            return True

        print(f"------------>images[{len(processed.images)}].seeds[{len(processed.all_seeds)}].subseeds[{len(processed.all_subseeds)}]")

        # opts.return_grid==true
        if len(processed.images) == len(processed.all_seeds) + 1:
            processed.images = processed.images[1:len(processed.images)]
            processed.infotexts = processed.infotexts[1:len(processed.infotexts)]
            # print(f"------------>processed.images.length resize")

        for i in range(len(processed.images)):
            image = processed.images[i]
            buffer = BytesIO()
            image.save(buffer, "png")
            image_bytes = buffer.getvalue()
            # base64_image = base64.b64encode(image_bytes).decode('ascii')
            seed = processed.all_seeds[i]
            subseed = processed.all_subseeds[i]
            print(f"image[{i}].seeds={seed}.subseed={subseed}.bytes_size={len(image_bytes)}.head=[{image_bytes[:16].hex(' ')}].tail=[{image_bytes[len(image_bytes) - 20:len(image_bytes) - 12].hex(' ')}]")
            # collection.hmset("RS:B:100:image", {"image": base64_image})
            # collection.hmset("RS:B:100:image:" + str(i), {str(seed): image_bytes})

        full = processed.js()
        print(f"postprocess --------------")
        print(f"processed => {full}")
        print(f"--------------------------")
        # regex = r"Steps:.*$"
        # info = re.findall(regex, processed.info, re.M)[0]
        # input_dict = dict(item.split(": ") for item in str(info).split(", "))
        # collection.hmset("RS:B:100:info", {"full": full, "info": info, "json": json.dumps(input_dict)})
        collection.hmset(str(prefix) + str(processed.seed), {"full": full})

        print(f"postprocess ---> Save2Redis.completed!")
        return True
