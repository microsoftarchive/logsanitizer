# logsanitizer

[![Build Status](https://travis-ci.org/wunderlist/logsanitizer.svg)](https://travis-ci.org/wunderlist/logsanitizer)
![Downloads](https://img.shields.io/pypi/dm/logsanitizer.svg)
![Version](https://img.shields.io/pypi/v/logsanitizer.svg)
![License](https://img.shields.io/pypi/l/logsanitizer.svg)

Log processing and sanitizer tool written in Python. Please take into consideration to use with **pypy** to get the best performance. It's working well in **Python 2.7 & 3.3+**.

This package does the following:
- Reads a log file line by line.
- Detects the dialect of every line individually.
- Filters and removes based on pre-defined rules.
- Classifies your logs (e.g.: determines event's name).
- Reformats your line and writes in a standardized format.

## Installation

You can use `pip` or `easy_install` to install this package.

```bash
$ pip install logsanitizer
```

## How to write a dialect

Since we don't provide any built-in dialect you have to write your own if you want to use this package for your work.

Let's see an example about how you can do this. For example your [nginx](https://www.nginx.com) creates lines in the following format where the `json_data` is containing the `user_id` and the `client_id`.

```
:timestamp :service_name :method :url :status_code :json_data
```

At first, you have to write a python file that describes your dialect. Call this file `nginx.py`.

```python
import json
import logsanitizer

class NginxLine(logsanitizer.Line):
    # Dialect's parse method to split the line into variables.
    @classmethod
    def parse(cls, classificator, line):
        return cls(classificator, *line.split(' ',5))

    # Constructor to load the line, if this function 
    # fails then this dialect will be skipped and it will
    # try to parse with the next dialect in order.
    def __init__(self, classificator, timestamp, service_name, method, url, status_code, data):
        # Call the parent function, it will set the `classificator` variable.
        super(NginxLine, self).__init__(classificator)

        # Save the basic information, remember the variable names.
        self.timestamp = timestamp
        self.service_name = service_name
        self.method = method
        self.url = url
        self.status_code = status_code
        
        # Parse the JSON file.
        json_data = json.loads(data)
        
        # Save the parsed variables into variables.
        self.user_id = json_data.get('user_id')
        self.client_id = json_data.get('client_id')

        self.event = None # Will be classified later.

	# Checks if it's the given dialect or not
    def is_type(self):
        return all([self.user_id, self.client_id])

    # Checks if it's a productional line or not
    def is_production(self):
        return 'production' in self.service_name

    # Defines the standardized CSV format that will be 
    # generated with this dialect. You may use the same
    # output for every dialect you have.
    def get_row(self):
        return [ self.user_id, self.client_id, self.event ]
```

Now, you have to create a Yaml configuration file for this dialect. Let's call this file `nginx.yaml`. The main idea behind this separation was to keep the format fixed and the rules easily changeable.

```yaml
# Header, please fill out these fields.
dialect: nginx
package: nginx.py
class: NginxLine

# Describe your classifications.
classifications:

# Use `match_` prefix to add equal condition between a 
# variable and it's value. In this case, it means the following:
# if line.url == '/projects':
#     line.event = 'ListProjects'
- match_url: /projects
  event: ListProjects

# Use the `pattern_` prefix to add a regular expression between
# a variable and it's value. In this case, it means the following:
# if re.match(r'^/projects/\d+$', line.url):
#     line.event = 'ViewProject'
- pattern_url: !regexp '^/projects/\d+$'
  event: ViewProject

# You can use the `{\d}` to refer the regular expression's group
# attribute.
- pattern_url: !regexp '^/projects/\d+/(.*)$'
  event: ViewProject.Page.{0}

# You can combine multiple conditions. They'll have an AND 
# relation, so every condition have to be fulfilled.
- pattern_url: !regexp '^/login/(.*)$'
  match_status: 302
  event: Login.Provider.{0}

# Ignores every following line where the `method` is `GET`.
- match_method: GET
  ignore: true

# No condition, it will only change the `event`'s value.
- event: OtherEvent
```

That's it. You can execute your script as

```bash
$ cat input-file.log | logsanitizer nginx.yml > output-file.log 
```

You can also use multiple dialects.

```bash
$ cat input-file.log | logsanitizer nginx.yml otherservice.yml > output-file.log 
```

## License

Copyright © 2016 Microsoft.

Distributed under the MIT License.

## Code of Conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
