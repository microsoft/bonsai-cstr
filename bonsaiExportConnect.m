% Script to configure exported Bonsai brain. Exported brains can be
% run in a few steps:
%   0. docker login with credentials and make sure docker is running on
%   local system
%   1. export your brain
%   2. start exported brain
%   3. configure the endpoint (defaults to localhost:5000) in
%   bonsaiConfig.m
%   4. run this script to configure an export session and set required variables
%   5. open the model and click "Run"

% Initial data required for compilation should be initialized
init_vars

% load model and disable fast restart
mdl = 'CSTR_Bonsai';
load_system(mdl);
set_param(mdl, 'FastRestart', 'off');

% configure exported brain
config = bonsaiConfig;
BonsaiConfigureExportConnect(config, mdl);
