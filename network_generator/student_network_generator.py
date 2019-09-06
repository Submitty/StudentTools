import os
import sys
import docker
import argparse
import shutil
import getpass
import json
from distutils.dir_util import copy_tree


def yes_or_no(question):
  """
  A simple helper function which returns True if the user enters 'yes',
  or False on anything else.
  """
  response = input(f'{question} (y/n) ').strip().lower()
  return True if response in ['y', 'yes'] else False

def generate_knownhosts_json(username, outer_name, containers, name_to_ip, container_directory, tcp_port, udp_port, filename):
  """
  Generates a knownhosts.json to aid in the initialization of student code.
  """
  knownhosts_dict = dict()
  knownhosts_dict['hosts'] = dict()

  # Add an entry for every container to the json file.
  for inner_name, inner_info in containers.items():
    ports = inner_info.get('number_of_ports', 1)

    if ports <= 0:
      raise SystemExit(f"ERROR ({inner_name}): Each host must be assigned 1 or more ports")

    ip_address = name_to_ip[inner_name][f'{username}_network']

    knownhosts_dict['hosts'][inner_name] = dict()
    knownhosts_dict['hosts'][inner_name]['tcp_start_port'] = tcp_port
    knownhosts_dict['hosts'][inner_name]['tcp_end_port']   = tcp_port + ports - 1
    knownhosts_dict['hosts'][inner_name]['udp_start_port'] = udp_port
    knownhosts_dict['hosts'][inner_name]['udp_end_port']   = udp_port + ports - 1
    knownhosts_dict['hosts'][inner_name]['ip_address']     = ip_address
    
    tcp_port = tcp_port + ports
    udp_port = udp_port + ports

  with open(filename, 'w') as outfile:
    json.dump(knownhosts_dict, outfile, indent=4)

def generate_knownhosts_txt(containers, container_directory, starting_port, filename):
  """
  Generates a knownhosts_xxx.txt (tcp or udp) to aid in the initialization of student code.
  """
  with open(filename, 'w') as outfile:
    for name, info in containers.items():
      ports = info.get('ports', 1)

      if ports <= 0:
        raise SystemExit("ERROR: Each host must be assigned 1 or more ports")

      if ports > 1:
        outfile.write(f'{name} {starting_port}-{starting_port + ports - 1}\n')
      else:
        outfile.write(f'{name} {starting_port}\n')

      starting_port = starting_port + ports


def create_container(username, container_name, container_info, working_directory, solution_directory):
  """
  Helper function used to create a single container.
  """

  client = docker.from_env()

  image = container_info['image']
  # We append the user's name to the container name to avoid conflicts w/ other users.
  full_container_name = f'{username}_{container_name}'
  # Each container mounts its own directory inside of working_dir
  container_dir = os.path.join(working_directory, container_name)

  os.makedirs(container_dir)
  copy_tree(solution_directory, container_dir)

  mount = {
    container_dir : {
      'bind' : container_dir,
      'mode' : 'rw'
    }
  }

  # Create the container
  container = client.containers.create(image, 
                                       command ='/bin/bash', 
                                       stdin_open = True,
                                       tty = True,
                                       volumes=mount,
                                       working_dir = container_dir, 
                                       hostname = container_name,
                                       name=full_container_name
                                      )
  return container

def create_network(username, network, working_directory, solution_directory):
  """
  Create and network the docker containers specified in the network config file.
  """

  client = docker.from_env()

  full_network_name = f'{username}_network'
  
  print('Removing old network...')
  try:
    old_network = client.networks.get(full_network_name)
    old_network.remove()
  except docker.errors.NotFound:
    pass


  # Variables to assign an ip address to each container.
  network_num = 10
  user_num = 1
  subnet = 1

  # Find a working network number (avoids conflicts if this script is being run
  # multiple times on the same machine).
  error = True
  while error:
    # Build a subnet on the docker network. Allows us to assign ip addresses.
    ipam_pool = docker.types.IPAMPool(
      subnet=f'{network_num}.{user_num}.{subnet}.0/24',)
    ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
    try:
      docker_network =  client.networks.create(full_network_name, ipam=ipam_config, driver='bridge', internal=True)
      error = False
    except:
      print(f'Error: could not build the network {network_num}.{user_num}.{subnet}.0/24')
      user_num += 1
      print(f'Trying {network_num}.{user_num}.{subnet}.0/24')
      pass

  print('Creating new containers...')
  # Host number for a container's ip, starting at 2 (can't start at 1).
  host = 2
  name_to_ip = dict()
  for container_name, container_info in network.items():
    # Create a docker container object using his container's container_info
    container = create_container(username, container_name, container_info, working_directory, solution_directory)
    
    ip = f'{network_num}.{user_num}.{subnet}.{host}'
    docker_network.connect(container, ipv4_address=ip, aliases=[container_name,])
    
    if not container_name in name_to_ip:
      name_to_ip[container_name] = dict()
    name_to_ip[container_name][full_network_name] = ip
    host += 1

  # Generating knownhosts files:
  for container_name, container_info in network.items():
    full_container_name = f'{username}_{container_name}'
    container_dir = os.path.join(working_directory, container_name)
    generate_knownhosts_json(username,
                             container_name,
                             network, 
                             name_to_ip, 
                             container_dir, 
                             9000, 
                             10000,  
                             os.path.join(container_dir, 'knownhosts.json'))

    # Create network configuration files within the container.
    generate_knownhosts_txt(network, container_dir, 9000,  os.path.join(container_dir,'knownhosts_tcp.txt'))
    generate_knownhosts_txt(network, container_dir, 10000, os.path.join(container_dir,'knownhosts_udp.txt'))


def main():
  parser = argparse.ArgumentParser(description='This utility will help you to quickly deploy docker networks to test student assignment submissions')
  parser.add_argument('network_specification_file',  help="The path to your network specification json.", type=str)
  args = parser.parse_args()

  working_directory = os.path.join(os.getcwd(), 'WORKING_DIRECTORY')
  client = docker.from_env()
  # Get the name of the user running the script to avoid name conflicts w/ other users on the system.
  username = getpass.getuser()

  if not os.path.exists(args.network_specification_file):
    raise SystemExit(f"ERROR: it looks like {args.network_specification_file} doesn't exist.")

  with open(args.network_specification_file, 'r') as infile:
    network_config = json.load(infile)

  if 'solution_directory' not in network_config:
    raise SystemExit(f"ERROR: please specify the full to your 'solution_directory' in your network config.")

  solution_directory = network_config['solution_directory']
  network = network_config['containers']

  if not os.path.isdir(solution_directory):
    raise SystemExit(f"ERROR: it looks like {solution_directory} doesn't exist.")

  if os.path.isdir(working_directory):
    # A safety feature to avoid removing a directory that the user wants around.
    # Remove at your own risk.
    if yes_or_no(f'It looks like {working_directory} already exists. Is it alright to remove it?') == False:
       raise SystemExit(f"Terminating.")
    shutil.rmtree(working_directory)

  os.mkdir(working_directory)

  print('Removing old containers...')  
  # Clean up docker networks and containers from previous runs
  for container_name in network.keys():
    full_container_name = f'{username}_{container_name}'
    try:
      old_container = client.containers.get(full_container_name)
      old_container.remove(force=True)
    except docker.errors.NotFound:
      continue

  print('Creating your network...')
  create_network(username, network, working_directory, solution_directory)

  print('To start your containers, run the following commands:')
  
  # Tell the user how to start their containers.
  for container_name, image in network.items():
    full_container_name = f'{username}_{container_name}'
    print(f'docker start -i --attach {full_container_name}')


if __name__ == '__main__':
  main()