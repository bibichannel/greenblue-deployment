#!/bin/python3
import docker
import subprocess
import argparse
import requests

######################################################################
### Setup variables
######################################################################
WEBHOOK_TOKEN_DISCORD = "https://discord.com/api/webhooks/1105406685490708531/QWSmNARZVGSDosEGcsZE_9qUe89802tRQnv9YBaEymwSUdm5aqUmXhXCnumZhV3F3-lu?thread_id=1105797029017428029"
DEFAULT_COLOR="blue"
DICT_PORT_BACKEND = {"development":"4000", "staging":"3000"}
######################################################################
### processing parser for command-line options, 
### arguments and sub-commands
######################################################################

def msg(name=None):
    return ''' 
    -------------------------------------
    WEB GATE INTERACT OPTIONS
    ./docker_exec.py \\
    --[enable/stop/disable]-gateway \\
    --file-yml=[docker-compose.yml file]

    ./docker_exec.py --restart-gateway

    DEPLOY BACKEND
    ./docker_exec.py \\
    --deploy \\
    --side=backend \\
    --file-yml=[docker-compose.yml file] \\
    --enviroment=[development/staging] \\
    --modify --file-conf=[nginx.conf file] \\   [Setup traffic flow for webgate container]
    --restart-gateway \\                        [Don't enable for first deploy]
    --stop-old-container \\                     [Don't enable for first deploy]
    --notification \\                           [Optional for deploy]
    --more-data=[STRING]                       [Optional for deploy]

    DEPLOY FRONTEND
    ./docker_exec.py \\
    --deploy \\
    --side=frontend \\
    --file-yml=[docker-compose.yml file] \\
    --enviroment=[development/staging] \\
    --notification \\                           [Optional for deploy]
    --more-data=[STRING]                       [Optional for deploy]

    MODIFY NGINX.CONF FILE TO PASS TRAFFIC TO NEW CONTAINER
    ./docker_exec.py \\
    --modify \\
    --side=backend \\
    --file-conf=[nginx.conf file] \\
    --enviroment=[development/staging]

    PUSH NOTIFICATION TO DISCORD SERVER 
    (Only use for case deploy backend/frontend)
    ./docker_exec.py --notification --more-data=[STRING]

    REMOVE UNTAGGED IMAGES
    ./docker_exec.py --remove

    -------------------------------------
    '''

parser = argparse.ArgumentParser(usage=msg())

required = parser.add_argument_group("Input request arguments")
required.add_argument("--side", metavar="", help="Deploy frontend/backend side with container, supported green/blue deployments: backend or frontend" )
required.add_argument("--file-yml", metavar="", help="Docker compose file or file path")
required.add_argument("--file-conf", metavar="", help="Nginx config file or file path")
required.add_argument("--enviroment", metavar="", help="Supported enviroment: development or staging")
required.add_argument("--more-data", metavar="", help="Add data for ")

flag = parser.add_argument_group('True/False arguments')
flag.add_argument("--enable-gateway", help= "Enable web gateway", action="store_true")
flag.add_argument("--stop-gateway", help= "Stop web gateway", action="store_true")
flag.add_argument("--restart-gateway", help= "Restart web gateway", action="store_true")
flag.add_argument("--disable-gateway", help= "Disable web gateway", action="store_true")
flag.add_argument("--deploy", help= "Deployment container", action="store_true" )
flag.add_argument("--stop", help= "Stop container", action="store_true" )
flag.add_argument("--stop-old-container", help= "Stop old container when deployed new container", action="store_true" )
flag.add_argument("--down", help="Down container", action="store_true")
flag.add_argument("--remove", help="Remove untagged images", action="store_true")
flag.add_argument("--modify", help="Edit the file to change traffic flow blue -> green or reverse", action="store_true")
flag.add_argument("--notification", help="Push notification to discord server", action="store_true")

args = parser.parse_args()

######################################################################
### processing docker
######################################################################

client = docker.from_env()

def remove_untagged_images():
    images = client.images.list(filters={"dangling": True})
    for image in images:
        if not image.tags:
            client.images.remove(image=image.id, force=True)

def search_containers_follow_side_running(side: str, environment: str):
    for container in client.containers.list(filters={"status":"running"}):
        if container.name.find(side) != -1 and \
            container.name.find(environment) != -1:
            print("search container name + ", container.name)
            color = "blue" if container.name.find("blue") != -1 else "green"
            return container, color
    return None, None

def search_containers_follow_side_not_running(side: str, environment: str):
    for container in client.containers.list(filters={"status":["exited", "paused"]}):
        if container.name.find(side) != -1 and \
            container.name.find(environment) != -1:
            print("search container name + ", container.name)
            color = "blue" if container.name.find("blue") != -1 else "green"
            return container, color
    return None, None

def search_containers_follow_subname(sub_name_containers):
    for container in client.containers.list():
        if container.name.find(sub_name_containers) != -1:
            return container.name
    return None

def check_container(name_container: str):
    return True if client.containers.get(name_container).status == "running" else False

######################################################################
### processing docker-compose
######################################################################

def enable_gateway(path_file: str):
    command = f'docker-compose --file={path_file} --project-name=gateway up -d --build'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return True if result.returncode == 0 else print(result.stderr); return False
    
def stop_gateway(path_file: str):
    command = f'docker-compose --file={path_file} --project-name=gateway stop'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return True if result.returncode == 0 else print(result.stderr); return False

def restart_gateway():
    name_gateway = search_containers_follow_subname(sub_name_containers="gateway")
    if name_gateway:
        command = f'docker exec -it {name_gateway} sh -c "nginx -s reload"'
        results = subprocess.run(command, shell=True, capture_output=True, text=True)
        return True if results.returncode == 0 else print(results.stderr); return False
    print("Don't search name gateway container") 
    return False
        
def disable_gateway(path_file: str):
    command = f'docker-compose --file={path_file} --project-name=gateway down'
    result = subprocess.run( command, shell=True, capture_output=True,  text=True)
    return True if result.returncode == 0 else print(result.stderr); return False

def deploy_container(dockerfile: str, environment: str, color: str):
    command = f'docker-compose --file={dockerfile} --project-name={color}-{environment} up -d --build'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result if result.returncode == 0 else print(result.stderr); return None

def stop_container(dockerfile: str, environment: str, color: str):
    command = f'docker-compose --file={dockerfile} --project-name={color}-{environment} stop'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result if result.returncode == 0 else print(result.stderr); return None

def down_container(dockerfile: str, environment: str, color: str):
    command = f'docker-compose --file={dockerfile} --project-name={color}-{environment} down'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result if result.returncode == 0 else print(result.stderr); return None

def get_name_container_from_result(result, side_deploy: str, environment: str, color: str):
    if result:
        my_lists = []
        my_lists += [item.split() for item in result.stdout.splitlines()]
        my_lists += [item.split() for item in result.stderr.splitlines()]

        for list_string in my_lists:
            for my_string in list_string:
                if my_string.find(side_deploy) != -1 and \
                my_string.find(environment) != -1 and \
                my_string.find(color) != -1:
                    return my_string
                
######################################################################
### processing discord
######################################################################

def send_message_to_discord(messages):
    data = {
        "content": messages,
        "username" : "IMSv2 Bot"
    }
    try:
        requests.post(WEBHOOK_TOKEN_DISCORD, data = data)
    except Exception as e:
        print(e)

gen_messages_container = lambda side_deploy, environment, message: \
    f"Deploy the **{side_deploy}** in the `{environment} environment`\n {message}"

######################################################################
### processing user-case input arguments 
######################################################################

# modify nginx.gateway.conf 
def file_modification_gateway(side_deploy: str, enviroment: str , port: str, shift_color: str, path_file: str) -> bool:
    current_color = "blue" if shift_color == "green" else "green"
    command = f'sed -i "s|proxy_pass http://{current_color}-{enviroment}-{side_deploy}-1:{port};|proxy_pass http://{shift_color}-{enviroment}-{side_deploy}-1:{port};|" {path_file}'
    results = subprocess.run(command, shell=True, capture_output=True, text=True)
    return True if results.returncode == 0 else print(results.stderr); return False

######################################################################
### main program
######################################################################

if __name__ == "__main__":
    current_color = DEFAULT_COLOR
    shift_color = DEFAULT_COLOR
    message_container = ""

    print(f"Default current-{current_color} | future-{shift_color}")
    if args.side == "backend" and args.enviroment:
        old_container, current_color = search_containers_follow_side_running(side=args.side, environment=args.enviroment)
        shift_color = "green" if current_color == "blue" else "blue"
    print(f"Change 01 current-{current_color} | future-{shift_color}")

    if args.down:
        old_container, current_color = search_containers_follow_side_not_running(side=args.side, environment=args.enviroment)
        print(f"Change 02 current-{current_color} | future-{shift_color}")
    
    if args.enable_gateway:
        if enable_gateway(args.file_yml):
            print("Enable web gateway successfuly")
    
    if args.stop_gateway:
        if stop_gateway(args.file_yml):
            print("Stop web gateway successfuly")

    if args.disable_gateway:
        if disable_gateway(args.file_yml):
            print("Disables web gateway successfuly")

    if args.remove:
        remove_untagged_images()
        print("Removed unttaged images")

    if args.deploy:
        if not args.side or not args.file_yml or not args.enviroment:
            print("Need argument --side, --file, --enviroment")
        elif args.side in ["backend", "frontend"] and args.file_yml is not None and args.enviroment in ["development","staging"]:
            result = deploy_container(dockerfile=args.file_yml, environment=args.enviroment, color=shift_color)
            name_ctn = get_name_container_from_result(result, side_deploy=args.side, environment=args.enviroment, color=shift_color)
            print(f"Deployed {name_ctn}")
            if check_container(name_ctn):
                message_container = f"The `{name_ctn}` is running"
            else: message_container = f"The `{name_ctn}` has failed"
        else: print("Not unexpected arguments")

    if args.modify:
        if not args.side or not args.enviroment or not args.file_conf:
            print("Need argument --side, --file and --enviroment")
        elif args.side in ["backend", "frontend"] and \
        args.file_conf is not None and\
        args.enviroment in ["development","staging"]:
            if file_modification_gateway(side_deploy=args.side,
                                         enviroment=args.enviroment,
                                         port=DICT_PORT_BACKEND[args.enviroment],
                                         shift_color=shift_color,
                                         path_file=args.file_conf):
                print("Modified successfully")
            else: print("Modified error")
        else: print("Not unexpected arguments")
    
    if args.restart_gateway:
        if restart_gateway():
            print("Restart web gateway successfuly")
            
    if args.stop or args.stop_old_container:
        if not args.side or not args.file_yml or not args.enviroment:
            print("Need argument --side, --file and --enviroment")
        elif args.side in ["backend", "frontend"] and args.file_yml is not None and args.enviroment in ["development","staging"]:
            result = stop_container(dockerfile=args.file_yml, environment=args.enviroment, color=current_color)
            if result:
                print(f"container {get_name_container_from_result(result, side_deploy=args.side, environment=args.enviroment, color=current_color)} stopped")
            else: print("container exited")
        else: print("Not unexpected arguments")
    
    if args.down:
        if not args.side or not args.file_yml or not args.enviroment:
            print("Need argument --side, --file and --enviroment")
        elif args.side in ["backend", "frontend"] and \
        args.file_yml is not None and \
        args.enviroment in ["development","staging"]:
            result = down_container(dockerfile=args.file_yml, environment=args.enviroment, color=current_color)
            if result:
                print(f"container {get_name_container_from_result(result, side_deploy=args.side, environment=args.enviroment, color=current_color)} removed")
            else: print("container exited")
        else: print("Not unexpected arguments")

    if args.notification:
        data = ""
        data += gen_messages_container(args.side, args.enviroment, message_container)
        if args.more_data:
            data += args.more_data
        send_message_to_discord(data)

