#### This application is a simple network generator for use by students taking network programming courses.

##### To run:
  0. Install and configure docker for your operating system.     
     __NOTE:__ Make certain you are in the ```docker``` group on your machine.
  1. Clone this repository to your local machine.
  2. Install this script's dependencies by running:        
     ```pip3 install -r requirements.txt```
  3. Configure a docker network within a ```network_config.json``` as described in the ```Network Configuration``` section
  4. Run the ```student_network_generator.py``` script, passing in the path to your ```network_config.json```.
  5. Run the commands output by the network generation script to be dropped into bash environments within your containers.
  6. Check regularly to see if new versions of this script have been released.
  7. __NOTE:__ If you encounter any errors while using the script, please ask about them first on your course forum, then, if it is indeed an error in this script, make an issue in this repository.


##### Network Configuration
  The network configuration has two fields, ```solution_directory``` and ```containers```.
  1. ```solution_directory``` is a string, and must be a full path to the solution code that you want copied into your container.

  2. ```containers``` is an object, where:
      1. Each key represents a unique container name which represents an object containing.
          1.  An ```image``` field, which specifies the docker image to be used in container creation.
          2. A ```ports``` field, which contains a positive, nonzero integer number of ports to be assigned to the container.

  Therefore, the following configuration:
  ```
  {
    "solution_directory" : "/path/to/my/solution/code",
    "containers" : {
      "alpha" : {
        "image" : "submittyrpi/csci4510:default",
        "ports" : 1
      },
      "beta" : {
        "image" : "submittyrpi/csci4510:default",
        "ports" : 1
      },
      "charlie" : {
        "image" : "submittyrpi/csci4510:default",
        "ports" : 1
      }
    }
  }
  ```

  Creates a network with three endpoints, ```alpha```, ```beta```, and ```charlie```, which are instantiated using the ```submittyrpi/csci4510:default``` container image, and which have 1 port in the resultant ```knownhost_tcp.txt``` and ```knownhost_udp.txt``` files.

  __NOTE:__ Only a value of ```1``` for ```ports``` is accepted at present by the network generator. Additional ports will be added in a future release.
  
