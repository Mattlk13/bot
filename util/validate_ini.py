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
    optional_fields = ["github", "homepage", "mainfile2"]

    validators = {
        "author": {
            "min": 2,
            "max": 30
        }
    }

    unaccepted_status_codes = [301, 302, 303, 308, 500, 501] + range(400, 500)

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

    def validate_mainfile(self, mainfiles, files, project):
        issues = []
        for version in files:
            if not any((mainfile in version["files"]) for mainfile in mainfiles):
                # print mainfile, str(version["files"]), str(mainfile in list(version["files"]))
                issues.append("Where is the {2}'s mainfile (*{1}*) in v-*{version}*".format(version["version"], mainfile, project))
        return issues

    def check_ini(self, repo, project_name, ref):
        url = "https://api.github.com/repos/{0}/contents/files/{1}?ref={2}".format(repo, project_name, ref)
        issues = []
        for item in requests.get(url).json():
            if item["type"] == "file" and item["name"] != "info.ini":
                issues.append("Unexpected file {path}".format(**item))
        return issues

    def validate_ini(self, ini_data=None, changed_files=[], project_name=None, owner_repo=None, ref=None):
        if project_name is None:
            project_name = ini_data["project"].lower()

        existing_project = self.get_project(project_name)
        issues = []

        if owner_repo:
            try:
                issues += self.check_ini(owner_repo, project_name, ref)
            except:
                pass
                
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
            if ini_data is not None:
                split = val.split("\"")
                if len(split) != 3 or split[0] != "" or split[2] != "":
                    issues.append("The {0} property should be wrapped in double quotes (e.g. `{0} = \"{1}\"`) and contain no other double quotes".format(key, val))

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
                        issues.append("{0} ('{1}') is too short".format(field, val))
                if "max" in validator:
                    if len(val) > validator["max"]:
                        issues.append("{0} ('{1}') is too long".format(field, val))

        #strip quotes
        if ini_data:
            ini = {k: v.strip("\"") for k, v in ini.iteritems()}

        if ini["github"]:
            if requests.get(ini["github"]).status_code in self.unaccepted_status_codes:
                issues.append("Couldn't retrieve `github` website [{github}]({github})".format(**ini))
        if ini["homepage"]:
            if requests.get(ini["homepage"]).status_code in self.unaccepted_status_codes:
                issues.append("Couldn't retrieve `homepage` website [{homepage}]({homepage})".format(**ini))

        #validate mainfile
        assets = existing_project["assets"] if existing_project and "assets" in existing_project else []
        #https://github.com/jsdelivr/api/issues/33
        mainfiles = [mainfile for key,mainfile in ini.iteritems() if key.startswith("mainfile")]
        files = self.get_library_files(new_version=changed_files, old_versions=assets)
        issues += self.validate_mainfile(mainfiles, files=files, project=project_name)

        return issues
