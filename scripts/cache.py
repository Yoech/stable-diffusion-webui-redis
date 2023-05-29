import base64
from io import BytesIO
import os
import re
import redis
import modules.scripts as scripts
import gradio as gr


def get_collection(host: str = '127.0.0.1', port: int = 6379, db: int = 0, password: str = '', max_connections: int = 10):
    conn_pool = redis.ConnectionPool(host=host, port=port, db=db, password=password, max_connections=max_connections)
    return redis.Redis(connection_pool=conn_pool)


class Scripts(scripts.Script):
    def title(self):
        return "Redis Storage"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        checkbox_save_to_redis = gr.inputs.Checkbox(label="Save to Redis", default=False)
        host = gr.inputs.Textbox(label="host", default="127.0.0.1")
        port = gr.inputs.Textbox(label="port", default=6379)
        db = gr.inputs.Textbox(label="db", default=0)
        password = gr.inputs.Textbox(label="password", default="")
        max_connections = gr.inputs.Textbox(label="max_connections", default=10)
        return [checkbox_save_to_redis, host, port, db, password, max_connections]

    def postprocess(self, p, processed, checkbox_save_to_redis, host, port, db, password, max_connections):
        collection = get_collection(host, port, db, password, max_connections) if checkbox_save_to_redis else None
        if collection is None:
            return True

        for i in range(len(processed.images)):
            image = processed.images[i]
            buffer = BytesIO()
            image.save(buffer, "png")
            image_bytes = buffer.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('ascii')
            print(f"bytes_size={len(image_bytes)},base64_size={len(base64_image)}")
            collection.hmset(self, "RS:B:100:image", base64_image)

        regex = r"Steps:.*$"
        info = re.findall(regex, processed.info, re.M)[0]
        input_dict = dict(item.split(": ") for item in str(info).split(", "))
        collection.hmset(self, "RS:B:100:info", info)

        processed.info = None
        processed.images = None
        collection.hmset(self, "RS:B:100:processed", processed)

        return True
