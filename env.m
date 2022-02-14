function value = env(key, default, useAutoEnvrep)
    % ENV - read environment variables
    %
    % Reads values from three sources in the following order:
    %  1) System environment (getenv)
    %  2) MATLAB preferences (getpref) in the 'env' group
    %  3) ".env" file on the path
    %
    % Examples:
    %  dbHost = env('DATABASE_HOST', '127.0.0.1');
    %  s3Pass = env('S3_PASSWORD');
    %  env PATH
    %
    % See also: getenv, getpref

    % Copyright 2021 Florian Schwaiger <f.schwaiger@tum.de>
    %
    % Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
    % associated documentation files (the "Software"), to deal in the Software without restriction,
    % including without limitation the rights to use, copy, modify, merge, publish, distribute,
    % sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
    % is furnished to do so, subject to the following conditions:
    %
    % The above copyright notice and this permission notice shall be included in all copies
    % or substantial portions of the Software.
    %
    % THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
    % BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    % NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    % DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    % OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

    if nargin > 2 && not(useAutoEnvrep)
        eval("envrep = @(x) x;");
    end

    narginchk(0, 2);
    if nargin == 0
        value = readfrominifile("*", pwd);
        value = structfun(@envrep, value, "Uniform", false);
        return
    end

    value = envrep(readfromsystemenv(key));
    if not(strcmp(value, ""))
        return
    end

    value = envrep(readfrommatlabpref(key));
    if not(strcmp(value, ""))
        return
    end

    value = envrep(readfrominifile(key, pwd));
    if not(strcmp(value, ""))
        return
    end

    if nargout > 0 && nargin > 1
        if isstring(key)
            value = string(default);
        else
            value = default;
        end
    elseif nargout > 0
        error('env:missing', ...
            'Environment value "%s" undefined, no default given.', key);
    end

end


function value = readfromsystemenv(key)
    % try to read from system env variables
    value = getenv(key);

    if isstring(key)
        value = string(value);
    end
end


function value = readfrommatlabpref(key)
    % read from MATLAB preferences "env" group
    if ispref('env', key)
        value = getpref('env', key);
    elseif isstring(key)
        value = "";
    else
        value = '';
    end
end


function value = readfrominifile(key, folder)
    % get the value from an ".env" file
    value = '';
    envFile = fullfile(folder, '.env');
    if not(exist(envFile, 'file'))
        parent = fileparts(folder);
        if strcmp(parent, folder)
            value = readfrominifile(key, parent);
        elseif strcmp(key, "*")
            value = struct();
        end
        return
    end

    modified = lastmodified(envFile);
    persistent envCache
    if isempty(envCache) || envCache.modified < modified
        envCache = struct( ...
            'modified', modified, ...
            'content', loadini(envFile) ...
        );
    end

    if strcmp(key, "*")
        value = envCache.content;
    elseif isfield(envCache.content, key)
        value = envCache.content.(key);
    end

    if isstring(key) && isstruct(value)
        value = structfun(@string, value, 'UniformOutput', false);
    elseif isstring(key)
        value = string(value);
    end
end


function modified = lastmodified(filename)
    % finds out when a file was modified last
    info = dir(filename);
    modified = info(1).datenum;
end


function value = loadini(filename)
    % read and parse a file in KEY=VALUE format
    lines = strsplit(fileread(filename), newline);
    value = struct();

    for iLine = 1:numel(lines)
        line = strtrim(lines{iLine});

        if isempty(line) || any(line(1) == '#;[')
            % ignore comments and section headers
        else
            value = appendlinevalue(value, line);
        end
    end
end


function parent = appendlinevalue(parent, line)
    [key, valueWithEqualsChar] = strtok(line, '=');
    key = strtrim(key);
    text = strtrim(valueWithEqualsChar(2:end));

    if isempty(text) || any(text(1) == '#;')
        % ignore unset value and comments
    elseif any(text(1) == '"''')
        % extract until the closing quote character
        parent.(key) = extractBefore(text(2:end), regexpPattern("(?<!\\)" + text(1)));
    else
        % apply
        parent.(key) = text;
    end
end

