from validate_ini import INIValidator
from validate_code import CodeValidator
from validate_version import VersionValidator

from os import path
import re

import requests

class ValidationState:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

valid_file_characters_re = re.compile(r"^[A-Za-z0-9.\-_/]+$")

class PullValidator(INIValidator, CodeValidator, VersionValidator):
    """
        Does the heavy lifting bringing together the components to validate a pr
    """

    def get_project(self, project):
        """
            Get project project from the api
        """
        data = requests.get("http://api.jsdelivr.com/v1/jsdelivr/libraries/{0}".format(project)).json()
        return data[0] if len(data) != 0 and type(data[0]) == dict else None

    def validate(self, pr):
        """
            validate a pull request for jsdelivr/jsdelivr
        """

        # did validation raise an exception somewhere?
        errored_out = False

        # e.g. megawac/jsdelivr
        owner_repo = "/".join(pr.head.repo)
        ref = pr.head.ref

        # collection of (<version>, <name>, <contents>)
        code_files = []
        # in case multiple
        ini_files = {}

        warnings = []

        # group files by project like api.jsdelivr.com/v1/jsdelivr/libraries for ease of iterating
        project_grouped = {}

        for pr_file in pr.iter_files():
            split_name = pr_file.filename.split("/")
            contents = requests.get(pr_file.raw_url).text
            ext = path.splitext(pr_file.filename)[1]
            name = "/".join(split_name[3:])
            project = split_name[1]
            version = split_name[2]

            data = {
                "contents": contents,
                "project": project,
                "version": version,
                "name": name,
                "extension": ext
            }

            if not pr_file.filename.islower():
                warnings.append("*{0}* should be lowercase".format(pr_file.filename))
            if not valid_file_characters_re.match(pr_file.filename):
                warnings.append("*{0}* contains illegal characters".format(pr_file.filename))

            if split_name[0] == "files" and len(split_name) > 3:
                code_files.append(data)

                if project not in project_grouped:
                    project_grouped[project] = []
                parent = project_grouped[project]
                
                vgroup = next((x for x in parent if x["version"] == version), None)
                if not vgroup:
                    parent.append({
                        "version": version,
                        "files": [name]
                    })
                else:
                    vgroup["files"].append(name)

                if pr_file.status == "modified": #the nerve
                    warnings.append("You appear to be changing the file contents of *{0}* in *{1}*!".format(name, version))

            elif ext == ".ini" and len(split_name) == 3:
                ini_files[project] = data

        checked = {}
        ini_issues = []
        for project_name,project in project_grouped.iteritems():
            checked[project_name] = True
            try:
                ini_issues += self.validate_ini(ini_files.get(project_name, None), changed_files=project, project_name=project_name, owner_repo=owner_repo, ref=ref)
            except Exception,e:
                errored_out = True
                ini_issues.append("Failed to validate {0}: {1}".format(project_name, str(e)))

        #ini file changed with no other files changed?
        for project,files in ini_files.iteritems():
            if project not in checked:
                try:
                    ini_issues += self.validate_ini(ini_data=files)
                except Exception,e:
                    errored_out = True
                    ini_issues.append("Failed to validate {0}: {1}".format(project_name, str(e)))

        try:
            code_issues = self.validate_code(code_files)
        except Exception,e:
            errored_out = True
            code_issues = [str(e)]

        version_issues = []
        for project_name,project in project_grouped.iteritems():
            version_issues += self.validate_version(project_name, project)
            # try:
            #     version_issues += self.validate_version(project_name, project)
            # except Exception,e:
            #     errored_out = True
            #     version_issues.append("Failed to validate {0}: {1}".format(project_name, str(e)))

        result = {
            "ini_issues": ini_issues,
            "file_issues": code_issues,
            "version_issues": version_issues,
            "warnings": warnings,

            "error_occured": errored_out
        }

        return ValidationState(**result)