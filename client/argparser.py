# Copyright (c) 2016, Corelight. All rights reserved.
#
# See COPYING for license information.
import argparse
import re
import sys
import textwrap

import client.util

def printHelp(self, parser, namespace, values=None, option_string=None): # pylint: disable=unused-argument
    args = vars(namespace)
    has_subcommand = ("command" in args or "component" in args)

    if parser.parent():
        path = parser.path()
    else:
        path = None

    usage = _formatUsage(path, has_subcommand)

    help = parser.format_help()
    help = re.sub("usage:.*", "Usage: " + usage, help)
    print(help)

    parser.exit()

argparse._HelpAction.__call__ = printHelp

def _wrap(txt):
    lines = ["\n".join(textwrap.wrap(line)) for line in txt.split("\n")]
    return "\n\n".join(lines)

_re_dquotes = re.compile("``([^`]+)``")
_re_squotes = re.compile("`([^`]+)`")
_re_backticks = re.compile("``([^']+)''")

def _display(txt):
    """
    Process a string that may contain reST control sequence for
    displaying to user. This apply a SmartPants-style filter; see
    http://daringfireball.net/projects/smartypants.
    """
    if not txt:
        return txt

    txt = _re_dquotes.sub(r'“\1”', txt)
    txt = _re_squotes.sub(r'“\1”', txt)
    txt = _re_backticks.sub(r'“\1”', txt)
    txt = txt.replace("--", "\u2013")
    txt = txt.replace("---", "\u2014")
    txt = txt.replace("...", "\u2026")
    return txt

def _formatUsage(path, has_subcommand):
    if not path:
        path = "<command>"

    addl = (" <subcommand>" if has_subcommand else "")
    return "{} [<global options>] {}{} [<options>]".format(client.NAME, path.strip(), addl)

def _buildArgument(parser, param):
    try:
        name = ("--" + param["name"])
    except KeyError:
        return

    server_type = param.get("type", "string")
    required = param.get("required", False)
    default_ = param.get("default", None)
    metavar = param.get("metavar", None)
    description = param.get("description", "")
    display = param.get("display", True)

    if display:
        help = _display(description)
    else:
        help = argparse.SUPPRESS

    if server_type == "flag":
        # Special-case: this doesn't take an argument.
        parser.add_argument(name, action="store_true", default=False, help=help)
        return

    type = {
        "bool": str, # sic! Don't want auto-conversion.
        "integer": int,
        "float": float,
        }.get(server_type, str)

    if not default_ is None:
        help +=" [Default: {}]".format(default_)

    if metavar:
        metavar = "<{}>".format(metavar)
    else:
        metavar = "<{}>".format(server_type)

    parser.add_argument(name, type=type, required=required, metavar=metavar, help=help, default=default_)

class ComponentArgumentParser(argparse.ArgumentParser):
    """
    The command line argument parser for a component's commands and options.
    """
    def __init__(self, **kwargs): # pylint: disable=unused-argument
        """Constructor."""
        super(ComponentArgumentParser, self).__init__(formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)

        self._resources = []
        self._parent = None
        self._path = ""
        self._subparsers_components = None
        self._subparsers_commands = None

        self.add_argument("-h", "--help", action='help', default=argparse.SUPPRESS,
                          help="Show this help message and exit.")

    def addResource(self, resource):
        """
        Adds a resource to the ones associated with this components. This then
        also updates the usage message. It also updates the parent parser.

        resource (list of dict): List of the resource meta dictionaries.
        """
        self._resources.append(resource)
        self.usage = self.format_usage()
        self.epilog = self.help_epilog()

        if self._parent:
            self._parent.addResource(resource)

    def addComponentParser(self, name):
        """Adds a new subparsers with a given name."""
        return self.componentParsers().add_parser(name)

    def componentParsers(self):
        if not self._subparsers_components:
            self._subparsers_components = self.add_subparsers(parser_class=ComponentArgumentParser, dest="component")

        return self._subparsers_components

    def commandParsers(self):
        """Returns the subparsers object for parsing commands."""
        if not self._subparsers_commands:
            self._subparsers_commands = self.add_subparsers(parser_class=CommandArgumentParser, dest="command")

        return self._subparsers_commands

    def setParent(self, parent):
        """
        Sets the parent component parser.

        parent (ComponentArgumentParser): The parent.
        """
        self._parent = parent

    def setPath(self, path):
        """
        Sets the usage path to the component parser.

        path (str): The past.
        """
        self._path = path

    def parent(self):
        """
        Returns the parent component parser or None if none.
        """
        return self._parent

    def path(self):
        """
        Returns the usage path to the component.
        """
        return self._path

    def format_usage(self):
        """Overridden from base class."""
        # Will be updated in HelpAction.
        return client.NAME

    def format_help(self):
        """Overridden from base class."""
        help = super(ComponentArgumentParser, self).format_help()
        help = re.sub(r"\n *\{.*\}\n", "\n", help)
        help = re.sub("positional arguments.*optional arguments", "optional arguments", help, flags=re.DOTALL)

        if self._parent:
            help = help.replace("optional arguments", "Options")
        else:
            # Why does pylint no like this?
            help = help.replace("optional arguments", "Global Options") # pylint: disable=no-member

        return help

    def print_help(self, file=None):
        """Overridden from base class."""
        usage = _formatUsage(None, True)
        help = self.format_help()
        help = re.sub("usage:.*", "Usage: " + usage, help)
        help += "\n" + self.help_epilog() + "\n"
        print(help, file=file)

    def help_epilog(self):
        """Overridden from base class."""
        if self.parent():
            epilog = "Subcommands:\n"
        else:
            epilog = "Commands:\n"

        previous_top_level_component = None

        if not self._resources and not self._parent:
            epilog += "\n"
            epilog += "  To see available commands, specify your Corelight Sensor's address with -b.\n"
            epilog += "  You can also set the CORELIGHT_DEVICE environment variable or create a\n"
            epilog += "  configuration file."
            return epilog

        for r in self._resources:
            if not r:
                continue

            summary = r.get("summary", "")
            top_level_component = r["component"][0]

            component = r["component"]

            p = self._parent
            while p:
                component = component[1:]
                p = p.parent()

            component = " ".join(component)

            if previous_top_level_component and previous_top_level_component != top_level_component:
                epilog += "\n\n"

            previous_top_level_component = top_level_component

            if not summary.endswith("."):
                summary += "."

            if r.get("requires-confirmation", False):
                summary += " (Requires confirmation.)"

            cmd = "{} {}".format(component, r["command"])
            epilog += "  {:25} {}\n".format(cmd, _display(summary))

        epilog += "\n\n  Use -h/--help with any subcommand to learn more about it."

        return epilog

    def error(self, message):
        print("{} error: {}".format(client.NAME, message), file=sys.stderr)
        self.exit(1)

class CommandArgumentParser(argparse.ArgumentParser):
    """
    The command line argument parser for a command's options.
    """
    def __init__(self, **kwargs): # pylint: disable=unused-argument
        """Constructor."""
        super(CommandArgumentParser, self).__init__(formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
        self._resource = None
        self._parent = None
        self._path = None

        self._request_fields = []
        self._response_fields = []

        self.add_argument("-h", "--help", action='help', default=argparse.SUPPRESS,
                          help="Show this help message and exit.")

    def setResource(self, resource):
        """
        Set the resources associate with the command. This then also updates
        the usage message.

        resource (dict): The resource meta dictionaries.
        """
        self._resource = resource

    def finalizeResource(self):
        """
        Finalizes intializing the resources. This then also updates the usage
        message.

        resource (dict): The resource meta dictionaries.
        """
        summary = _wrap(_display(self._resource.get("summary", "")))
        description = _wrap(_display(self._resource.get("description", "")))

        if self._resource.get("requires-confirmation", True):
            description += " Before executing the operation, the command will request explicit confirmation."

        self.description = "{}\n\n{}".format(summary, description)
        self.epilog = self.help_epilog()

    def parent(self):
        """
        Returns the parent component parser or None if none.
        """
        return self._parent

    def setParent(self, parent):
        """
        Sets the parent component parser.

        parent (ComponentArgumentParser): The parent.
        """
        self._parent = parent

    def path(self):
        """
        Returns the usage path to this parser.
        """
        return self._path

    def setPath(self, path):
        """
        Sets the usage path to this parser.

        path (str): The past.
        """
        self._path = path

    def addRequestField(self, field):
        """
        Adds a request field associated with the command.

        field (dict) The field meta dictionary.
        """
        if not self._request_fields:
            self.add_argument("-r", "--read-stdin", action='store_true', default=False, dest="stdin",
                              help="Read data as JSON from standard input.")

        self._request_fields += [field]

    def addResponseField(self, field):
        """
        Adds a response field associated with the command.

        field (dict) The field meta dictionary.
        """
        schema = self._resource.get("schema", None)

        if not self._response_fields and (schema != "object-raw"):
            self.add_argument("-j", "--json", action='store_true', default=False, dest="json",
                              help="Output result in JSON.")

        self._response_fields += [field]

    def format_usage(self):
        """Overridden from base class."""
        # Will be updated in HelpAction.
        return client.NAME

    def format_help(self):
        """Overridden from base class."""
        help = super(CommandArgumentParser, self).format_help()
        help = help.replace("optional arguments", "Options")
        help = re.sub(re.compile("positional arguments.*Options", re.DOTALL), "Options", help)
        help = re.sub(re.compile("^ *\{help\}.*$\\n", re.MULTILINE), "", help)
        return help

    def help_epilog(self):
        """Overridden from base class."""
        for f in self._request_fields:
            _buildArgument(self, f)

        if not self._response_fields:
            return

        schema = self._resource["schema"]

        if schema == "collection":
            epilog = "Output is a list of objects each with the following possible fields:\n\n"
        else:
            epilog = "Output fields:\n\n"

        fields = [(f["name"], f) for f in self._response_fields]
        tuples = []

        for (name, f) in sorted(fields):
            ty = f.get("type", None)
            display = f.get("display", True)

            if not display:
                # We don't show these.
                continue

            description = _display(f.get("description", ""))

            x = "{} ({})".format(name, ty)
            y = description

            tuples.append((x, y))

        epilog += client.util.formatTuples(tuples)

        return epilog

    def error(self, message):
        print("{} error: {}".format(client.NAME, message), file=sys.stderr)
        self.exit(1)

def createParser(config):
    """
    Creates the top-level command line argument parser. This parser is barely
    populated initially with only a few static options that always apply.

    Returns: A new ``ComponentArgumentParser`` for the top level.
    """

    device = config.get("device", None)
    user = config.get("user", None)
    password = config.get("password", None)
    ssl_ca_cert = config.get("ssl-ca-cert", None)
    ssl_no_verify_hostname = config.get("ssl-no-verify-hostname", False)
    ssl_no_verify_certificate = config.get("ssl-no-verify-certificate", False)

    parser = ComponentArgumentParser()
    parser.add_argument("-b", "--device", action="store", dest="device", default=device,
                        help="Name or IP address of your Corelight Sensor.")
    parser.add_argument("-v", "--version", action="store_true",
                        help="Show version of the API client software.")
    parser.add_argument("-d", "--debug", action="count", dest="debug_level",
                        help="Increase level of debugging output.")
    parser.add_argument("-a", "--async", action="store_true", dest="async_nowait",
                        help="Do not wait for asynchronous operations to finish.")
    parser.add_argument("-u", "--user", action="store", dest="user", default=user,
                        help="User name for authentication.")
    parser.add_argument("-p", "--password", action="store", dest="password", default=password,
                        help="Password for authentication.")
    parser.add_argument("--ssl-ca-cert", action="store", dest="ssl_ca_cert", default=ssl_ca_cert,
                        help="Path to CA certificate(s) for verifying device identity. Defaults to Corelight's internal CA. Specify 'system' for system's root store.")
    parser.add_argument("--ssl-no-verify-certificate", action="store_true", dest="ssl_no_verify_certificate", default=ssl_no_verify_certificate,
                        help="Do not verify device's certificate.")
    parser.add_argument("--ssl-no-verify-hostname", action="store_true", dest="ssl_no_verify_hostname", default=ssl_no_verify_hostname,
                        help="Do not verify device's hostname for certificate check.")
    parser.add_argument("--cache", action="store", dest="cache", default=None,
                        help="Location where to store meta cache.")

    # Legacy BroBox support. To be removed.
    parser.add_argument("--brobox", action="store", dest="brobox", default=None,
                        help=argparse.SUPPRESS)

    return parser

ComponentParsers = {}

def populateParser(parser, meta):
    """
    Extend a previously created top-level command line argument parser with
    options derived from the meta information downloaded from a Corelight Sensor. This
    fills in most of the command & options that the command client supports.

    parser (ComponentArgumentParser): The parser to extend, which must have
    been previously created with ``createtopLevelParser()``.

    meta (meta.Meta): The complete meta information downloaded from a Corelight Sensor.

    Returns: Nothing.
    """
    commands = []

    for (_, resources) in meta:
        for r in resources:
            components = r["component"]
            command = r["command"]
            commands += [(components, command, r)]

    for (components, command, r) in sorted(commands):
        component_parser = addComponentParser(parser, "", components)
        addCommandParser(component_parser, command, r)

    help = parser.componentParsers().add_parser("help")
    help.set_defaults(parser_for_help=parser)

def addComponentParser(current_parser, current_path, components):
    if not components:
        return current_parser

    (head, tail) = (components[0], (components[1:] if len(components) > 1 else []))

    path = current_path + " " + head
    component_parser = ComponentParsers.get(path, None)

    if not component_parser:
        component_parser = current_parser.addComponentParser(head)
        component_parser.setParent(current_parser)
        component_parser.setPath(path)
        ComponentParsers[path] = component_parser

        if tail:
            help_parent = component_parser.componentParsers()
        else:
            help_parent = component_parser.commandParsers()

        help = help_parent.add_parser("help")
        help.set_defaults(parser_for_help=component_parser)

    return addComponentParser(component_parser, path, tail)

def addCommandParser(component_parser, command, resource):
    command_parsers = component_parser.commandParsers()

    summary = resource.get("summary", None)

    if resource.get("requires-confirmation", False):
        summary += " (Requires confirmation.)"

    command_parser = command_parsers.add_parser(command, help=_display(summary), dest=command)
    command_parser.setParent(component_parser)
    command_parser.setResource(resource)
    command_parser.set_defaults(resource=resource)

    for p in resource.get("parameters", []):
        _buildArgument(command_parser, p)


    for f in resource.get("request-fields", []):
        command_parser.addRequestField(f)

    for f in resource.get("response-fields", []):
        command_parser.addResponseField(f)

    for v in resource.get("variables", []):
        _buildArgument(command_parser, v)

    command_parser.finalizeResource()

    if command:
        command_parser.setPath(component_parser.path() + " " + command)

    component_parser.addResource(resource)

    help_parser = command_parser.add_subparsers()
    help = help_parser.add_parser("help")
    help.set_defaults(parser_for_help=command_parser)
