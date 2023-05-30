import base64
from io import BytesIO
import os
import re
import redis
import modules.scripts as scripts
import gradio as gr

redis_save = os.environ.get('REDIS_SAVE', False)
redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
redis_port = os.environ.get('REDIS_PORT', 6379)
redis_db = os.environ.get('REDIS_DB', 0)
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
                with gr.Row():
                    checkbox_save_to_redis = gr.Checkbox(label="Enable", value=bool(redis_save))
                    host = gr.Textbox(label="Host", default=redis_host)
                    port = gr.Textbox(label="Port", default=redis_port)
                    db = gr.Textbox(label="Db", default=redis_db)
                    password = gr.Textbox(label="Password", default=redis_auth)
        return [checkbox_save_to_redis, host, port, db, password]

    def postprocess(self, p, processed, checkbox_save_to_redis, host, port, db, password):
        print(f"postprocess ---> Save2Redis[{redis_save}]")
        collection = get_collection(host, port, db, password) if checkbox_save_to_redis else None
        if collection is None:
            return True

        for i in range(len(processed.images)):
            image = processed.images[i]
            buffer = BytesIO()
            image.save(buffer, "png")
            image_bytes = buffer.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('ascii')
            print(f"bytes_size={len(image_bytes)},base64_size={len(base64_image)}")
            # collection.hmset("RS:B:100:image", {"image": base64_image})
            collection.hmset("RS:B:100:image", {"image": image_bytes})

        regex = r"Steps:.*$"
        info = re.findall(regex, processed.info, re.M)[0]
        input_dict = dict(item.split(": ") for item in str(info).split(", "))
        collection.hmset("RS:B:100:info", {"info": info})

        print(f"postprocess ---> Save2Redis.completed!")
        return True
