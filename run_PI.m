%% Run the Chemical Process Optimization sample without Bonsai
clear; clc;

%% Initialize Workspace 
init_vars

%% SCENARIO 1: Using Gain Scheduled PI

% To prevent thermal runaway while ramping down the residual concentration,
% use feedback control to adjust the coolant temperature |Tc| based on
% measurements of the residual concentration |Cr| and reactor temperature |Tr|.
% For this application, we use a cascade control architecture where
% the inner loop regulates the reactor temperature and the outer loop tracks
% the concentration setpoint. Both feedback loops are digital with a 
% sampling period of 0.5 minutes.

sim('CSTR_PI')

% Calculate metrics
rms = sqrt(mean((simout(:, 1) - simout(:, 2)).^2));
disp(['Gain Scheduled PI with 0% noise: Target Concentration followed with RMS of: ', num2str(rms)])

rms = sqrt(mean((simout(:, 3) - simout(:, 4)).^2));
disp(['Gain Scheduled PI with 0% noise: Target Reactor Temperature followed with RMS of: ', num2str(rms)])

plot_results(tout, simout, 'Gain scheduled PI with 0% noise')

%% SCENARIO 2: Benchmark (with 5% noise)

noise = 5;
conc_noise = abs(CrEQ(1)-CrEQ(5)) * noise / 100.0;
temp_noise = abs(TrEQ(1)-TrEQ(5)) * noise / 100.0;

sim('CSTR_PI')

% Calculate metrics
rms = sqrt(mean((simout(:, 1) - simout(:, 2)).^2));
disp(['Gain Scheduled PI with 5% noise: Target Concentration followed with RMS of: ', num2str(rms)])

rms = sqrt(mean((simout(:, 3) - simout(:, 4)).^2));
disp(['Gain Scheduled PI 5% noise: Target Reactor Temperature followed with RMS of: ', num2str(rms)])

plot_results(tout, simout, ['Gain scheduled PI with ', num2str(noise), '% noise'])
