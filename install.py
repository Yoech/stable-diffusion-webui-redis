import launch

if not launch.is_installed("redis"):
    launch.run_pip("install redis", "requirements for stable-diffusion-webui-redis")