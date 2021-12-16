"""
Author: Jeremy Cornett
Date: 2017-09-26
Purpose: Create/reconfigure a Jenkins node using desired SSH connection defaults. The approach in code is to conform 
with a desired state approach (i.e. rerunning this script won't hurt anything).
http://python-jenkins.readthedocs.io/en/latest/index.html
"""

import argparse
import certifi
import jenkins
import requests
import time
from xml.etree import ElementTree


def set_element_text(tree, tag, text):
    """Set the text of an XML tag in the given XML tree. Create the tag if it doesn't exist.
    :param tree: The XML tree.
    :type tree: xml.etree.ElementTree
    :param tag: The name of the element tag to search for.
    :type tag: str
    :param text: The text to place in the element.
    :type text: str
    :return: None
    """
    element = tree.find(tag)
    if element is None:
        if "/" in tag:
            raise Exception("Tag '{}' is too complex for this script to handle.".format(tag))
        else:
            element = ElementTree.SubElement(tree, tag)
    element.text = text


def set_element_attrib(tree, tag, attrib, text):
    """Set the attribute text of an XML tag in the given XML tree. Create the tag if it doesn't exist.
    :param tree: The XML tree.
    :type tree: xml.etree.ElementTree
    :param tag: The name of the element tag to search for.
    :type tag: str
    :param attrib: The name of the attribute on the element to modify.
    :type attrib: str
    :param text: The text to place in the element.
    :type text: str
    :return: None
    """
    element = tree.find(tag)
    if element is None:
        if "/" in tag:
            raise Exception("Tag '{}' is too complex for this script to handle.".format(tag))
        else:
            ElementTree.SubElement(tree, tag, attrib={attrib: text})
    else:
        element.attrib[attrib] = text


if __name__ == "__main__":
    # Parse the command line arguments.
    parser = argparse.ArgumentParser(description="Create/Reconfig a node on a Jenkins master. This does NOT support "
                                                 "renaming of nodes or deleting nodes. This simply looks for a node "
                                                 "name. If it exists, update it's info. If it doesn't exist, "
                                                 "create it.")
    parser.add_argument("url", help="The URL of the Jenkins master.")
    parser.add_argument("username", help="The name of a user on the Jenkins instance.")
    parser.add_argument("password", help="The user's password.")
    parser.add_argument("sshCredentialID", help="The ID of an existing credential object to use for SSH connections to "
                                                "the node.")
    parser.add_argument("name", help="The intended name of the node.")
    parser.add_argument("description", help="The description of the node.")
    parser.add_argument("labels", help="The labels to apply to the node, which is used for determining where to run "
                                       "jobs.")
    parser.add_argument("host", help="The IP or DNS name of the node to be used for SSH connections to it.")
    parser.add_argument("--ca-cert", help="The path to a CA certificate to verify for connections with the "
                                          "Jenkins master.")
    parser.add_argument("-n", "--num-executors", default="1", help="")
    parser.add_argument("-f", "--force", action="store_true", help="Force the deletion and full recreation of "
                                                                   "the node.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Display additional information.")
    parser.add_argument("-p", "--path", default="/jenkins",
                        help="The default path Jenkins will use on the node for the workspace and associated files.")
    parser.add_argument("-m", "--mode", default="EXCLUSIVE", help="The mode in which to connect the node to the "
                                                                  "master.")
    parser.add_argument("-o", "--port", default="22", help="The port to use for SSH connections.")
    parser.add_argument("-r", "--retention-strategy", default="Always", help="The node retention strategy.")
    parser.add_argument("-t", "--host-strategy",
                        default="hudson.plugins.sshslaves.verifiers.ManuallyTrustedKeyVerificationStrategy",
                        help="The host key verification stategy the Jenkins master should use when connecting with SSH"
                             " to the node.")
    parser.add_argument("-q", "--manual-verify", default="false",
                        help="Require manual acceptance of the node's SSH key on the Jenkins master.")
    args = parser.parse_args()

    # Connect to the Jenkins server.
    server = jenkins.Jenkins(args.url, username=args.username, password=args.password)

    # The process for obtaining the crumb doesn't use the OS cert store. It uses the ca bundle packaged in certifi.
    # Disabling the SSL verification is one workaround.
    # os.environ.setdefault("PYTHONHTTPSVERIFY", "0")
    # The appropriate way is to modify the bundle being used by certifi.
    # https://incognitjoe.github.io/adding-certs-to-requests.html
    # https://requests.readthedocs.io/en/master/user/advanced/#ca-certificates
    if args.ca_cert and len(args.ca_cert) != 0:
        try:
            test = requests.get(args.url)
        except requests.exceptions.SSLError as err:
            cafile = certifi.where()
            if args.verbose:
                print("CERT {}".format(args.ca_cert))
                print("CERTIFI {}".format(cafile))
                print
            with open(args.ca_cert, 'rb') as infile:
                customca = infile.read()
            with open(cafile, 'ab') as outfile:
                outfile.write(b'\n')
                outfile.write(customca)
            test = requests.get(args.url)

    # Delete the node if required.
    if args.force and server.node_exists(args.name):
        server.delete_node(args.name)
        if args.verbose:
            print("Force delete of node {}.".format(args.name))
            print()

    # If the node doesn't already exist, create it.
    if not server.node_exists(args.name):
        params = {
            'port': args.port,
            'credentialsId': args.sshCredentialID,
            'host': args.host
        }
        server.create_node(
            args.name,
            nodeDescription=args.description,
            numExecutors=args.num_executors,
            remoteFS=args.path,
            labels=args.labels,
            exclusive=(args.mode == "EXCLUSIVE"),
            launcher=jenkins.LAUNCHER_SSH,
            launcher_params=params)

    # There are some node settings that can't be done with the above method.
    # Once the base node exists, get it's config and modify it to apply
    # the remainder of the configuration.

    # We can assume the node exists, but we cannot assume it is already configured correctly.
    str_xml_node_config = server.get_node_config(args.name)
    if args.verbose:
        print("BEFORE MOD")
        print("----------")
        print(str_xml_node_config)
        print()

    ''' EXAMPLE CONFIG SSH
    <?xml version="1.0" encoding="UTF-8"?>
    <slave>
      <name>slave2</name>
      <description>my test slave</description>
      <remoteFS>/jenkins</remoteFS>
      <numExecutors>2</numExecutors>
      <mode>EXCLUSIVE</mode>
      <retentionStrategy class="hudson.slaves.RetentionStrategy$Always"/>
      <launcher class="hudson.plugins.sshslaves.SSHLauncher" plugin="ssh-slaves@1.21">
        <host>my.jenkins.slave1</host>
        <port>22</port>
        <credentialsId>jenkins-nodes-ssh</credentialsId>
        <maxNumRetries>0</maxNumRetries>
        <retryWaitTime>0</retryWaitTime>
        <sshHostKeyVerificationStrategy class="hudson.plugins.sshslaves.verifiers.ManuallyTrustedKeyVerificationStrategy">
          <requireInitialManualTrust>false</requireInitialManualTrust>
        </sshHostKeyVerificationStrategy>
      </launcher>
      <label>precise</label>
      <nodeProperties/>
    </slave>
    '''

    # Load the node's config into an xml tree for ease of manipulation.
    tree_node_config = ElementTree.fromstring(str_xml_node_config)

    # Set all the original data again.
    set_element_text(tree_node_config, "description", args.description)
    set_element_text(tree_node_config, "remoteFS", args.path)
    set_element_text(tree_node_config, "numExecutors", args.num_executors)
    set_element_text(tree_node_config, "mode", args.mode)
    set_element_text(tree_node_config, "launcher/host", args.host)
    set_element_text(tree_node_config, "launcher/port", args.port)
    set_element_text(tree_node_config, "launcher/credentialsId", args.sshCredentialID)
    set_element_text(tree_node_config, "label", args.labels)

    # Set the additional configurations.
    set_element_attrib(tree_node_config, "retentionStrategy", "class",
                       "hudson.slaves.RetentionStrategy${}".format(args.retention_strategy))
    element_launcher = tree_node_config.find("launcher")
    set_element_attrib(element_launcher, "sshHostKeyVerificationStrategy", "class", args.host_strategy)
    element_strategy = element_launcher.find("sshHostKeyVerificationStrategy")
    set_element_text(element_strategy, "requireInitialManualTrust", args.manual_verify)

    # Double check that the changes were made.
    str_xml_node_config_mod = ElementTree.tostring(tree_node_config, encoding='utf-8')
    if args.verbose:
        print("AFTER MOD")
        print("----------")
        print(str_xml_node_config_mod)
        print()

    # Reconfig the node.
    server.reconfig_node(args.name, str_xml_node_config_mod)

    # Double check that the changes were made.
    str_xml_node_config_mod = server.get_node_config(args.name)
    if args.verbose:
        print("DOUBLE CHECK MOD")
        print("----------")
        print(str_xml_node_config_mod)
        print()

    # Wait till the node is online.
    loop = 0
    if args.verbose:
        print("Wait for node to come online", end='')
    while True:
        if loop > 30:
            raise Exception("Node did not come online (timeout 30 seconds).")
        json_node_info = server.get_node_info(args.name)
        if json_node_info["offline"]:
            time.sleep(1)
            loop += 1
            if args.verbose:
                print(".", end='')
        else:
            break
    if args.verbose:
        print()

    # Enable the node.
    server.enable_node(args.name)
    if args.verbose:
        print()
        print("Enable the node {}".format(args.name))
