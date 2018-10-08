# logsanitizer

[![Build Status](https://travis-ci.org/wunderlist/logsanitizer.svg)](https://travis-ci.org/wunderlist/logsanitizer)
![Downloads](https://img.shields.io/pypi/dm/logsanitizer.svg)
![Version](https://img.shields.io/pypi/v/logsanitizer.svg)
![License](https://img.shields.io/pypi/l/logsanitizer.svg)

Log processing and sanitizer tool written in Python.
While this tool works in Python 2.7 and 3.3+, consider using PyPy for better performance.

This package helps perform various operations on your logs:

- Read a log file line by line
- Detect the dialect of every line individually
- Filter based on pre-defined rules
- Classify your logs (i.e. determine event's name)
- Reformat your line into a standardized format

## Installation

You can use `pip` or `easy_install` to install this package.

```bash
$ pip install logsanitizer
```

## How to write a dialect

Since we don't provide any built-in dialect you have to write your own if you want to use this package for your work.

Let's see an example of how you can do this.
For example, your [nginx](https://www.nginx.com) creates lines in the following format where the `json_data` contains `user_id` and `client_id` fields:

```
:timestamp :service_name :method :url :status_code :json_data
```

First, you have to write a Python class that describes your dialect.
Call this file `nginx.py`.

```python
import json
import logsanitizer

class NginxLine(logsanitizer.Line):
    @classmethod
    def parse(cls, classificator, line):
        """Define how to split each line into variables"""
        return cls(classificator, *line.split(' ', 5))

    def __init__(self, classificator, timestamp, service_name, method, url, status_code, data):
        """
        Constructor for loading the line.
        If this function fails then this dialect will be skipped,
        and the next dialect in the order will be tried.
        """

        # Call the parent constructor, which will set the `classificator` variable.
        super(NginxLine, self).__init__(classificator)

        self.timestamp = timestamp
        self.service_name = service_name
        self.method = method
        self.url = url
        self.status_code = status_code

        json_data = json.loads(data)

        self.user_id = json_data.get('user_id')
        self.client_id = json_data.get('client_id')

        self.event = None # Will be classified later.

    def is_type(self):
        """Check if the line is of the expected dialect"""
        return all([self.user_id, self.client_id])

    def is_production(self):
        """Check if the line is productional or not"""
        return 'production' in self.service_name

    def get_row(self):
        """
        Define the fields that will be generated when outputting in CSV format.
        This is useful for standardizing the shape of output for all your dialects.
        """
        return [self.user_id, self.client_id, self.event]
```

Now, you have to create a YAML configuration file for this dialect.
Let's call this file `nginx.yaml`.
The main idea behind this separation was to keep the format fixed and the rules easily changeable.

```yaml
# Header, please fill out these fields.
dialect: nginx
package: nginx.py
class: NginxLine

# Describe your classifications.
classifications:

# Use `match_` prefix to add equal condition between a variable and it's value.
# In this case, it means the following:
# if line.url == '/projects':
#     line.event = 'ListProjects'
- match_url: /projects
  event: ListProjects

# Use the `pattern_` prefix to add a regular expression between a variable and it's value.
# In this case, it means the following:
# if re.match(r'^/projects/\d+$', line.url):
#     line.event = 'ViewProject'
- pattern_url: !regexp '^/projects/\d+$'
  event: ViewProject

# You can use `{\d}` to refer the regular expression's group
# attribute.
- pattern_url: !regexp '^/projects/\d+/(.*)$'
  event: ViewProject.Page.{0}

# You can combine multiple conditions.
# They'll have an AND relation, so every condition has to be fulfilled.
- pattern_url: !regexp '^/login/(.*)$'
  match_status: 302
  event: Login.Provider.{0}

# Ignores every following line where the `method` is `GET`.
- match_method: GET
  ignore: true

# No condition; it will only change the `event`'s value.
- event: OtherEvent
```

That's it!
You can now reformat your logs with the following command:

```shell
$ cat input-file.log | logsanitizer nginx.yml > output-file.log
```

You can also use multiple dialects.

```shell
$ cat input-file.log | logsanitizer nginx.yml otherservice.yml > output-file.log
```

## License

Copyright © 2016 Microsoft.

Distributed under the MIT License.

## Code of Conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
