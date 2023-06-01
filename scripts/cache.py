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

        with gr.Group():
            with gr.Accordion("Redis Configure", open=True):
                #with gr.Box():
                    with gr.Row():
                        #checkbox_save_to_redis = gr.inputs.Checkbox(label="Enable", default=redis_save)
                        checkbox_save_to_redis = gr.Checkbox(label="Enable", value=redis_save)
                    with gr.Group():
                        with gr.Row():
                            #host = gr.inputs.Textbox(label="Host", default=redis_host)
                            host = gr.Textbox(label="Host", value="Host Address")
                            #port = gr.inputs.Textbox(label="Port", default=redis_port)
                            port = gr.Textbox(label="Port", value="what")
                            #db = gr.inputs.Textbox(label="db", default=redis_db)
                            db = gr.Textbox(label="Db", value=redis_db)
                            #password = gr.inputs.Textbox(label="Password", default=redis_auth)
                            password = gr.Textbox(label="Password", value=redis_auth)
        return [checkbox_save_to_redis, host, port, db, password]

    def postprocess(self, p, processed, checkbox_save_to_redis, host, port, db, password):
        print(f"------------>checkbox_save_to_redis[{checkbox_save_to_redis}]")
        print(f"------------>host[{host}]")
        print(f"------------>port[{port}]")
        print(f"------------>db[{db}]")
        print(f"------------>password[{password}]")
        collection = get_collection(host, port, db, password) if checkbox_save_to_redis else None
        if collection is None:
            return True

        print(f"------------>images[{len(processed.images)}].seeds[{len(processed.all_seeds)}].subseeds[{len(processed.all_subseeds)}]")
        for i in range(len(processed.images)):
            image = processed.images[i]
            buffer = BytesIO()
            image.save(buffer, "png")
            image_bytes = buffer.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('ascii')
            # seed = processed.all_seeds[i]
            # subseed = processed.all_subseeds[i]
            # print(f"image[{i}].seeds={seed}.subseed={subseed}.bytes_size={len(image_bytes)}.base64_size={len(base64_image)}")
            print(f"image[{i}].bytes_size={len(image_bytes)}.base64_size={len(base64_image)}.last_bytes=[{image_bytes[len(image_bytes)-8:].hex(' ')}]")
            # collection.hmset("RS:B:100:image", {"image": base64_image})
            # collection.hmset("RS:B:100:image:" + str(i), {str(seed): image_bytes})

        full = processed.js()
        print(f"postprocess --------------")
        print(f"processed => {full}")
        print(f"--------------------------")
        regex = r"Steps:.*$"
        info = re.findall(regex, processed.info, re.M)[0]
        input_dict = dict(item.split(": ") for item in str(info).split(", "))
        # collection.hmset("RS:B:100:info", {"full": full, "info": info, "json": json.dumps(input_dict)})
        collection.hmset("RS:B:100:info", {"full": full})

        print(f"postprocess ---> Save2Redis.completed!")
        return True
