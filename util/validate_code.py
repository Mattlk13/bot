import re

# from https://github.com/hamilyon/status/blob/master/grin.py
# TEXTCHARS = ''.join(map(chr, [7,8,9,10,12,13,27] + range(0x20, 0x100)))
# ALLBYTES = ''.join(map(chr, range(256)))

# def is_binary_string(bytes):
#     bytes = bytes[:1024] #hack patch #3
#     if isinstance(bytes, unicode):
#         bytes = bytes.encode("ascii", errors="ignore")
#     return bool(bytes.translate(ALLBYTES, TEXTCHARS))

comment_re = re.compile(r"(?:\/\*(?:[\s\S]*?)\*\/)|(?:([\s;])+\/\/(?:.*)$)", re.MULTILINE)


class CodeValidator():
    warn_statements = [] #[r"\bprompt\(\b", r"\balert\(\b", r"\bconfirm\(\b", r"document\.write"]

    # true binary, false non binary
    valid_extensions = {
        ".css": False,
        ".js": False,
        ".map": False,


        #flash
        ".png": True,
        ".jpg": True,
        ".jpeg": True,
        ".gif": True,
        ".ico": True,
        ".webp": True,
        ".webm": True,

        #fonts
        ".otf": True,
        ".eot": True,
        ".ttf": True,
        ".woff": True,
        ".woff2": True,
        ".cur": True,

        #etc
        ".svg": False,
        ".swf": True
    }

    def validate_code(self, files):
        issues = []

        for file in files:
            is_fresh = self.is_fresh_project(file['project'])

            if file["name"] == "mainfile" and file["extension"] == "":
                continue
            if is_fresh and file["extension"].lower() not in self.valid_extensions:
                issues.append("*{extension}* (on *{name}*) seems odd to want to host?".format(**file))
                continue
            elif file["contents"] is None:
                # Disabled this chekc due to unreliable detection of file size changes in the github pull
                # request api. Static files with additions will sometimes have 0 changes despite clearly being
                # changed in large PRs. See #55
                    # if self.valid_extensions.get(file["extension"]) != True:
                    #     issues.append("Expected *{name}* to be static content; found binary".format(**file))
                continue #binary file
            elif self.valid_extensions.get(file["extension"]) != False:
                issues.append("Expected *{name}* to be binary content; found text".format(**file))
                continue

            if file["contents"].strip() == "":
                issues.append("Why is *{name}* an empty file?".format(**file))

            if file["extension"] != ".js" and file["extension"] != ".css":
                continue
            
            if re.search(r"\bmin\b", file["name"]):
                #warn if more than 20 lines and the average line width is not long
                l = file["contents"].splitlines(True)
                if len(l) >= 50 and (sum(len(r) for r in l) / len(l)) <= 200:
                    print(len(l))
                    issues.append("Is {name} ({version}) properly minimized?".format(**file))

            for test in self.warn_statements:
                if re.search(test, file["contents"]):
                    issues.append("Expression `{0}` had a match in the contents of *{name}* ({version}).".format(test, **file))

            #no comments... could be more sound by checking start
            # if not comments_re.search(file["contents"]):
            #     issues.append("*{name}* ({version}) probably should start with a header detailing author and code source".format(**file))

        return issues

