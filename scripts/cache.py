import base64
from io import BytesIO
import os
import re
import redis
import modules.scripts as scripts
import gradio as gr

redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
redis_port = os.environ.get('REDIS_PORT', 6379)
redis_db = os.environ.get('REDIS_DB', 0)
redis_auth = os.environ.get('REDIS_AUTH', '')

def get_collection(host: str = '127.0.0.1', port: int = 6379, db: int = 0, password: str = ''):
    print(f"get_collection--->host[{host}].port[{port}].db[{db}].password[{password}]")
    conn_pool = redis.ConnectionPool(host=host, port=port, db=db, password=password, max_connections=10)
    return redis.Redis(connection_pool=conn_pool)


class Scripts(scripts.Script):
    def title(self):
        return "Redis Storage"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        checkbox_save_to_redis = gr.inputs.Checkbox(label="Save to Redis", default=True)
        host = gr.inputs.Textbox(label="host", default=redis_host)
        port = gr.inputs.Textbox(label="port", default=redis_port)
        db = gr.inputs.Textbox(label="db", default=redis_db)
        password = gr.inputs.Textbox(label="password", default=redis_auth)
        return [checkbox_save_to_redis, host, port, db, password]

    def postprocess(self, p, processed, checkbox_save_to_redis, host, port, db, password):
        print(f"host[{host}].port[{port}].db[{db}].password[{password}]")
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

        # processed.info = None
        # processed.images = None
        # collection.hmset("RS:B:100:processed", {"processed": processed})

        return True
