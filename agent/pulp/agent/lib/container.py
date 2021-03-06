from logging import getLogger
import imp
import os

from pulp.common.config import ANY, BOOL, Config, OPTIONAL, REQUIRED, SectionNotFound, Validator


_logger = getLogger(__name__)


# handler roles
SYSTEM = 0
CONTENT = 1
BIND = 2
# (ROLE, property)
ROLE_PROPERTY = (
    (SYSTEM, 'system'),
    (CONTENT, 'content'),
    (BIND, 'bind'))
# ALL roles
ROLES = [r[0] for r in ROLE_PROPERTY]


class Descriptor:
    """
    Content handler descriptor and configuration.
    @cvar ROOT: The default directory contining descriptors.
    @type ROOT: str
    @cvar SCHEMA: The descriptor schema
    @type SCHEMA: schema
    @ivar name: The content unit name
    @type name: str
    @ivar cfg: The raw INI configuration object.
    @type cfg: L{Config}
    """

    ROOT = '/etc/pulp/agent/conf.d'

    SCHEMA = (
        ('main', REQUIRED,
            (
                ('enabled', REQUIRED, BOOL),
            )),
        ('types', REQUIRED,
            (
                ('system', OPTIONAL, ANY),
                ('content', OPTIONAL, ANY),
                ('distributor', OPTIONAL, ANY),
            )),
    )

    @classmethod
    def list(cls, root=ROOT):
        """
        Load the handler descriptors.
        @param root: The root directory contining descriptors.
        @type root: str
        @return: A list of descriptors.
        @rtype: list
        """
        descriptors = []
        cls.__mkdir(root)
        for name, path in cls.__list(root):
            try:
                descriptor = cls(name, path)
                if not descriptor.enabled():
                    continue
                descriptors.append((name, descriptor))
            except:
                _logger.exception(path)
        return descriptors

    @classmethod
    def __list(cls, root):
        """
        Load the handler descriptors.
        @param root: The root directory contining descriptors.
        @type root: str
        @return: A list of descriptors.
        @rtype: list
        """
        files = os.listdir(root)
        for fn in sorted(files):
            part = fn.split('.', 1)
            if len(part) < 2:
                continue
            name, ext = part
            if ext not in ('.conf'):
                continue
            path = os.path.join(root, fn)
            if os.path.isdir(path):
                continue
            yield (name, path)

    @classmethod
    def __mkdir(cls, path):
        """
        Ensure the descriptor root directory exists.
        @param path: The root directory contining descriptors.
        @type path: str
        """
        if not os.path.exists(path):
            os.makedirs(path)

    def __init__(self, name, path):
        """
        @param name: The handler name.
        @type name: str
        @param path: The absolute path to the descriptor.
        @type path: str
        """
        cfg = Config(path)
        validator = Validator(self.SCHEMA)
        validator.validate(cfg)
        self.name = name
        self.cfg = cfg

    def enabled(self):
        """
        Get whether the handler is enabled.
        @return: True if enabled.
        @rtype: bool
        """
        return self.cfg['main']['enabled']

    def types(self):
        """
        Get a list of supported content types.
        @return: A dict of supported type IDs.
            {role=[types,]}
        @rtype: dict
        """
        types = {}
        section = self.cfg['types']
        for role, property in ROLE_PROPERTY:
            if property not in section:
                continue
            listed = section[property]
            split = [t.strip() for t in listed.split(',')]
            types[role] = [t for t in split if t]
        return types


class Typedef:
    """
    Represents a handler type definition.
    @ivar cfg: The type specific content handler configuration.
        This is basically the [section] defined in the descriptor.
    @type cfg: INIConfig
    """

    def __init__(self, cfg, section):
        """
        Construct the object and validate the configuration.
        @param cfg: The descriptor configuration.
        @type cfg: Config
        @param section: The typedef section name within the descriptor.
        @type section: str
        """
        schema = (
            (section, REQUIRED,
                (
                    ('class', REQUIRED, ANY),
                ),
             ),)
        cfg = Config(cfg, filter=[section])
        if cfg:
            validator = Validator(schema)
            validator.validate(cfg)
            self.cfg = cfg[section]
        else:
            raise SectionNotFound(section)


class Container:
    """
    A content handler container.
    Loads and maintains a collection of content handlers
    mapped by type_id.
    @cvar PATH: A list of directories containing handlers.
    @type PATH: list
    @ivar root: The descriptor root directory.
    @type root: str
    @ivar path: The list of directories to search for handlers.
    @type path: list
    @ivar handlers: A mapping of type_id to handler.
    @type handlers: tuple (content={},distributor={})
    @ivar raised: A list of handler loading exceptions.
    @type raised: list
    """

    PATH = [
        '/usr/lib/pulp/agent/handlers',
        '/usr/lib64/pulp/agent/handlers',
    ]

    def __init__(self, root=Descriptor.ROOT, path=PATH):
        """
        @param root: The descriptor root directory.
        @type root: str
        @param path: The list of directories to search for handlers.
        @type path: list
        """
        self.root = root
        self.path = path
        self.handlers = {}
        self.raised = []
        self.reset()

    def reset(self):
        """
        Reset (empty) the container.
        """
        d = {}
        for r in ROLES:
            d[r] = {}
        self.handlers = d
        self.raised = []

    def load(self):
        """
        Load and validate content handlers.
        """
        self.reset()
        for name, descriptor in Descriptor.list(self.root):
            self.__load(name, descriptor)

    def find(self, type_id, role=CONTENT):
        """
        Find and return a content handler for the specified
        content type ID.
        @param type_id: A content type ID.
        @type type_id: str
        @return: The content type handler registered to
            handle the specified type ID.
        @rtype: L{Handler}
        """
        role = self.handlers.get(role, {})
        return role.get(type_id)

    def all(self, *roles):
        """
        All handlers.
        @param roles: A list of roles to include.
            Empty list = ALL
        @type roles: list
        @return: A list of (<type_id>,<handler>).
        @rtype: list
        """
        all = []
        for role in (roles or ROLES):
            all += self.handlers[role].items()
        return all

    def errors(self):
        """
        Get a list of (exceptions) errors raised during
        handler loading.
        @return: A list of raised exceptions
        @rtype: list
        """
        return self.raised

    def __load(self, name, descriptor):
        """
        Load the handler defined by the name and descriptor.
        The modules defining the handler classes are loaded from defined
        handler installation directories.  If not found there, the class
        property is expected to be fully package qualified so that the
        classes can be loaded from the python path.
        @param name: The handler name.
        @type name: str
        @param descriptor: A handler descriptor.
        @type descriptor: L{Descriptor}
        """
        try:
            mod = self.__load_module(name)
            provided = descriptor.types()
            for role, types in provided.items():
                for type_id in types:
                    typedef = Typedef(descriptor.cfg, type_id)
                    path = typedef.cfg['class']
                    if mod is None:
                        mod = self.__import_module(path)
                    Handler = getattr(mod, path.rsplit('.')[-1])
                    handler = Handler(typedef.cfg)
                    self.handlers[role][type_id] = handler
        except Exception, e:
            self.raised.append(e)
            _logger.exception('handler "%s", import failed', name)

    def __load_module(self, name):
        """
        Load (import) from source the module by name.
        @param name: The module name.
        @type name: str
        @return: The module (or None)
        """
        mod = None
        path = self.__find_module(name)
        if path:
            mangled = self.__mangled(name)
            mod = imp.load_source(mangled, path)
        return mod

    def __import_module(self, path):
        """
        Import and return the specified class.
        @param path: A package qualified class reference.
        @return: The leaf module (or None)
        """
        path = path.rsplit('.', 1)
        mod = __import__(path[0], globals(), locals(), [path[-1]])
        return mod

    def __mangled(self, name):
        """
        Mangle the module name to prevent (python) name collisions.
        @param name: A module name.
        @type name: str
        @return: The mangled name.
        @rtype: str
        """
        n = hash(name)
        n = hex(n)[2:]
        return ''.join((name, n))

    def __find_module(self, name):
        """
        Find a handler module by searching the directories in the container's path.
        @param name: The module name.
        @type name: str
        @return: The path to the module or None when not found.
        @rtype: str
        """
        file_name = '.'.join((name, 'py'))
        for dir_path in self.path:
            path = os.path.join(dir_path, file_name)
            if os.path.exists(path):
                _logger.info('using module at: %s', path)
                return path
