# jenkins-node-ssh

Setup the host as a Jenkins SSH node and connect the Jenkins master to it. 
This is the preferred method of connecting a node to the Jenkins master as the master initiates the connections
and can reconnect easily.

## Requirements

The Jenkins master already exists, basic setup is complete, and the credential object for SSH node connections exists.

## Role Variables

### REQUIRED
* jenkins_node_master_url: The URL to the Jenkins master this node will connect with.
* jenkins_node_master_user: A user on the Jenkins master that has enough permissions to add a node. 
* jenkins_node_master_password: The password for the user on the Jenkins master. This should be vaulted.
* jenkins_node_credential: The ID of a credential object which has the user 'jenkins' and associated password 
  which will be used to connect from the master to the node over SSH
* jenkins_node_user_password: The password for the 'jenkins' user to be created on the node. 

Make sure you get those passwords vaulted so they're not in plain text!

### OPTIONAL
* jenkins_node_name: The name for the node. This defaults to the ansible host name.
* jenkins_node_description: The description for the node. The default is blank.
* jenkins_node_executors: The number of executors for the node. This defaults to 1.
* jenkins_node_labels: The labels to apply for the node. Multiple labels should be separated by a space. 
  This defaults to the ansible host name.
* jenkins_node_host: The DNS/IP address for the node. This defaults to the ansible host's default IPV4 address.
* jenkins_node_master_ca_cert: The path to the CA certificate for verifying SSL connections with the master, if needed.
* jenkins_node_user: The user name for connecting to this Jenkins instance.
* jenkins_node_user_groups: Specify the groups the the jenkins user should be in. 
  Useful for adding the user to groups (like docker) that get setup by other ansible roles (like docker-host).
* jenkins_node_openjdk_major_version: The major version of OpenJDK to install. This defaults to the same major version
  that the jenkins master role uses.
* jenkins_node_openjdk_full_version: The full version of OpenJDK to install. Defaults to "latest" but you can provide a
  specific version if you like. EX: "11.0.6.10"

## Dependencies

None

## Example Playbook

Again, make sure you get those passwords vaulted so they're not in plain text!

      hosts: docker01
      vars:
        jenkins_node_master_address: https://jenkins.COMPANY.com
        jenkins_node_master_user: admin
        jenkins_node_master_password: Password1
        jenkins_node_credential: jenkins-nodes-ssh
        jenkins_node_user_password: Password2
      roles:
        - role: jenkins-node-ssh

## License

BSD-3-Clause

## Author Information

Jeremy Cornett <jeremy.cornett@forcepoint.com>
