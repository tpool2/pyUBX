#!/usr/bin/env python3
"""Generate CPP code from the UBX message defintions in UBX/."""
import os
import sys
import re
import datetime
import inspect
from introspect import getClassesInModule, getClassName, getClassMembers
import UBX

__version__ = "0.1"


def fixClassName(name):
    """Remove the double 'class' names.

    E.g. UBX.CFG.CFG.PM2 becomes UBX.CFG.PM2.
    """
    l = name.split(".")
    del l[2]
    return ".".join(l)


def isFieldType(obj):
    """Test if object is a Type in a Field."""
    return obj.__class__.__module__ == 'Types'


def isFieldRepeated(obj):
    """Test if object is a Repeated 'type' in a Field."""
    if inspect.isclass(obj):
        return getClassName(obj).split(".")[-1] == "Repeated"
    else:
        return False


def makeComment(s):
    """Comment out a (multiline) string."""
    if s is None or s == "":
        return None
    l = s.split("\n")
    if len(s) == 1:
        l[0] = "/* " + l + " */"
    else:
        l[0] = "/* " + l[0]
        l[1:] = [" * " + ss for ss in l[1:]]
        l.append(" */")
    return "\n".join(l)


def makeMemberDecl(typ, name):
    """Return a member declaration.

    In particular rearrange the pseudo .ctype such as char[10]."""
    m = re.match(r"(.*)(\[[-0-9]+\])", typ)
    if m is not None:
        typ, ary = m.groups()
        return "{} {}{};".format(typ, name, ary)
    else:
        return "{} {};".format(typ, name)


def makeMessageStruct(file, className, Message, indent=4):
    messageName = fixClassName(getClassName(Message)).replace("UBX."+className+".", "")
    if messageName == className:
        messageName = messageName + "_"
    fullClassName = "{}::{}".format(className, messageName)
    if Message.__doc__ is not None:
        file.write(makeComment(Message.__doc__))
    file.write("struct {}\n".format(fullClassName))
    file.write("{\n")
    _id = Message._id
    _class = Message._class
    fields = getClassMembers(Message.Fields)
    fieldsNotRepeated = list(filter(lambda f: not isFieldRepeated(f[1]), fields))
    repeated = list(filter(lambda f: isFieldRepeated(f[1]), fields))
    fieldsNotRepeated = sorted(fieldsNotRepeated, key=lambda x: x[1].ord)
    for field in fieldsNotRepeated:
        file.write("    {}\n".format(makeMemberDecl(field[1].ctype, field[0])))
    if repeated:
        repeated = repeated[0]
        file.write("\n    struct Repeated {\n")
        makeStructBodyRepeated(file, repeated[1])
        file.write("    };\n")
        file.write("    typedef _iterator<{}::Repeated> iterator;\n".format(fullClassName))
        file.write("    static _iterator<Repeated> iter(char*data, size_t size) {\n")
        file.write("        return _iterator<Repeated>(data+sizeof({c}), size-sizeof({c}));\n".format(c=fullClassName))
        file.write("    }\n")
        file.write("    static size_t size(size_t n) {{ return sizeof({c}) + n*sizeof({c}::Repeated); }}\n".format(c=fullClassName))
    file.write("\n    static uint8_t classID;\n")
    file.write("    static uint8_t messageID;\n")
    file.write("};\n\n")
    file.write("uint8_t {}::classID   = 0x{:02X};\n".format(fullClassName, _class))
    file.write("uint8_t {}::messageID = 0x{:02X};\n".format(fullClassName, _id))
    file.write("\n");


def makeStructBodyRepeated(file, Repeated):
    fields = getClassMembers(Repeated)
    fields = sorted(fields, key=lambda x: x[1].ord)
    for name, Type in fields:
        file.write("        {}\n".format(makeMemberDecl(Type.ctype, name)))


if __name__ == '__main__':
    for Cls in getClassesInModule(UBX):
        className = fixClassName(getClassName(Cls)).replace("UBX.", "")
        fileName = "lang/cpp/src/messages/{}.h".format(className)
        file = open(fileName, 'w')
        file.write("// File {}\n".format(fileName))
        file.write("// Auto-generated by pyUBX {} v{} on {}\n".format(
            os.path.basename(__file__),
            __version__,
            datetime.datetime.now().isoformat())
            )
        file.write("// See https://github.com/mayeranalytics/pyUBX\n")
        ifndefName = "__"+className.upper()+"_H__"
        file.write("\n#ifndef {}\n".format(ifndefName));
        file.write("#define {}\n".format(ifndefName));
        file.write("\n#include <stdint.h>\n")
        file.write("#include \"../UBX.h\"\n\n")
        if Cls.__doc__ is not None:
            file.write(makeComment(Cls.__doc__) + "\n")
        file.write("struct {}\n".format(className))
        file.write("{\n")
        for _, Message in getClassMembers(Cls, inspect.isclass):
            messageName = fixClassName(getClassName(Message)).replace("UBX."+className+".", "")
            if messageName == className:
                messageName = messageName + "_"
            file.write("    struct {};\n".format(messageName))
        file.write("};\n\n")

        for name, Message in getClassMembers(Cls, inspect.isclass):
            if name == className:
                name = name + "--------------"
            makeMessageStruct(file, className, Message)

        file.write("#endif // ifndef {}\n".format(ifndefName));
        file.close()
        sys.stderr.write("Wrote {}\n".format(fileName))

    # make parseUBX.h
    fNames = list()
    fileName = "lang/cpp/src/parseUBX.h"
    file = open(fileName, 'w')
    file.write("// File {}\n".format(fileName))
    file.write("// Auto-generated by pyUBX {} v{} on {}\n".format(
        os.path.basename(__file__),
        __version__,
        datetime.datetime.now().isoformat())
        )
    file.write("// See https://github.com/mayeranalytics/pyUBX\n")
    # ifndef
    ifndefName = "__PARSEUBX_H__"
    file.write("#ifndef {}\n".format(ifndefName))
    file.write("#define {}\n".format(ifndefName))
    file.write("\n")
    file.write("#include \"../src/parseUBXBase.h\"")
    file.write("\n")
    # include all files
    for Cls in getClassesInModule(UBX):
        className = fixClassName(getClassName(Cls)).replace("UBX.", "")
        file.write("#include \"messages/{}.h\"\n".format(className))
    file.write("\n")
    # ParseUBX class
    file.write("class ParseUBX : public ParseUBXBase\n")
    file.write("{\n")
    file.write("public:\n")
    file.write("    ParseUBX(char* const buf, const size_t BUFLEN) : ParseUBXBase(buf, BUFLEN) {};\n")
    file.write("\n")
    file.write("private:\n")
    file.write("    void onUBX(uint8_t cls, uint8_t id, size_t len, char buf[]) {\n")
    file.write("        switch(cls) {\n")
    for Cls in getClassesInModule(UBX):
        className = fixClassName(getClassName(Cls)).replace("UBX.", "")
        file.write("        case 0x{:02X}: // Message class {}\n".format(Cls._class, className))
        file.write("            switch(id) {\n")
        for messageName, Message in getClassMembers(Cls, inspect.isclass):
            if messageName == className:
                messageName = messageName + "_"
            fName = "on{}_{}".format(className, messageName)
            fNames.append((fName, className, messageName))
            cppClassName = "{}::{}".format(className, messageName)
            file.write("            case 0x{:02X}: // Message {}-{}\n".format(Message._id, className, messageName))
            file.write("                {}(*(({}*)buf));\n".format(fName, cppClassName))
            file.write("                break;\n".format(name))
        file.write("            default:\n")
        file.write("                onUBXerr(cls, id, len, NotImplemented);\n")
        file.write("            }\n")
        file.write("            break;\n")
    file.write("        default:\n".format(Cls._class))
    file.write("            onUBXerr(cls, id, len, NotImplemented);\n")
    file.write("        }\n")
    file.write("    }\n")
    file.write("\n")
    file.write("public:\n")
    for fName, className, messageName in fNames:
        file.write("    /* callback for {}::{} messages */\n".format(className, messageName))
        file.write("    virtual void {}({}::{}& msg) {{}}\n".format(fName, className, messageName))
        file.write("    \n")
    file.write("private:\n")
    file.write("    ParseUBX();\n")
    file.write("};\n")
    file.write("\n")
    file.write("#endif // #define {}\n".format(ifndefName))
    file.write("\n")
    file.close()
    sys.stderr.write("Wrote {}\n".format(fileName))
