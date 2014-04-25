import os
import requests

#simple naive parser
def read_ini(contents):
    result = {}
    for line in contents.splitlines(True):
        split = line.split("=") 
        if len(split) > 1: #last line
            prop = split[0].strip()
            val = split[1].strip()
            result[prop] = val
    return result

class INIValidator():

    required_fields = ["author", "description", "mainfile"]
    optional_fields = ["github", "homepage"]

    validators = {
        "author": {
            "min": 2,
            "max": 30
        }
    }

    def get_library_files(self, new_version=[], old_versions=None):
        #merge by version
        versions = []
        map = {}
        for version in new_version:
            map[version["version"]] = version.copy()
            versions.append(map[version["version"]])
        for version in old_versions:
            if version["version"] in map:
                files = map[version["version"]]["files"]
                # merge files
                for file in version["files"]:
                    if file not in files:
                        files.append(file)
            else:
                versions.append(version)

        return versions

    def validate_mainfile(self, mainfile, files=None):
        if files is None:
            files = self.get_library_files(library)
        issues = []
        for version in files:
            if mainfile not in version["files"]:
                # print mainfile, str(version["files"]), str(mainfile in list(version["files"]))
                issues.append("where is the project's mainfile (*{1}*) in version *{0}*".format(version["version"], mainfile))
        return issues

    def validate_ini(self, ini_data=None, changed_files=[], project_name=None):
        if project_name is None:
            project_name = ini_data["project"].lower()

        existing_project = self.get_project(project_name)
        issues = []

        if ini_data:
            try:
                ini_data["contents"].decode("ascii")
            except: # UnicodeDecodeError
                issues.append("`info.ini` for {project} contains non-ascii characters".format(**ini_data))
                return issues
            ini = read_ini(ini_data["contents"])
        elif type(existing_project) is dict:
            fields = self.required_fields + self.optional_fields
            ini = {k: existing_project.get(k, None) for k in fields}
        else:
            issues.append("{0} has no *info.ini* file buddy".format())
            return issues

        for key, val in ini.iteritems():
            if ini_data and not (val.startswith("\"") and val.endswith("\"")):
                issues.append("The {0} property should be wrapped in double quotes (i.e. {0} = \"{1}\")".format(key, val))

            #not a known key?
            if key not in self.required_fields and key not in self.optional_fields:
                issues.append("{0} isn't a valid *info.ini* property...".format(key))

        for field in self.required_fields:
            if not ini.get(field, False): # doesnt exist or is falsey
                issues.append("No {0} property provided".format(field))

            elif field in self.validators:
                validator = self.validators[field]
                val = ini[field].strip("'\"")

                if "min" in validator:
                    if len(val) < validator["min"]:
                        issues.append("{0} ('{1}') is to short".format(field, val))
                if "max" in validator:
                    if len(val) > validator["max"]:
                        issues.append("{0} ('{1}') is to short".format(field, val))


        #validate mainfile
        if existing_project and "assets" in existing_project:
            assets = existing_project["assets"]
        else:
            assets = []

        files = self.get_library_files(new_version=changed_files, old_versions=assets)
        issues += self.validate_mainfile(ini["mainfile"].strip("\""), files=files)

        return issues

