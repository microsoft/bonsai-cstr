function value = envrep(value)
    % Substitute environment variables in the given string.
    %
    %   string = envrep(string)
    %
    % The variables must be defined in the string in one of
    % the following schemas:
    %
    %   ${NAME_WITH_UNDERSCORES}
    %   ${NAME_WITH_UNDERSCORES:default}
    %   $NAME_WITH_UNDERSCORES
    %
    % This tool is autmoatically used with env() as well,
    % allowing you to have environment variables that
    % point to other environment variables, especially
    % in your .env configuration file.
    %
    % See also env

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

    wasChar = ischar(value);
    wasCell = iscell(value);
    value = string(value);

    for iValue = 1:numel(value)
        [vars, starts, ends] = regexp(value(iValue), "\$(?<name>\w[\w\d_]*)|\$\{(?<name>\w[\w\d_]*)(?<default>:.*?)?\}", "names", "start", "end");

        for k = numel(vars):-1:1
            if isempty(vars(k).default) || vars(k).default == ""
                replacement = env(vars(k).name);
            else
                replacement = env(vars(k).name, extractAfter(vars(k).default, 1));
            end

            value(iValue) = replaceBetween(value(iValue), starts(k), ends(k), replacement);
        end
    end

    if wasChar
        value = char(value);
    elseif wasCell
        calue = cellstr(value);
    end
end
