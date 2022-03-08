%% Run the sample with benchmark and brain and plot results
% This script can be run once you have trained, exported, and are locally
% running a brain.
% This script will run 4 simulation scenarios:
% 1st: Gain scheduled PI without noise
% 2nd: Gain scheduled PI with noise (as configured below)
% 3rd: Brain with no noise
% 4th: Brain with noise (as configured below)

clear; close all; clc;

%% Set simulation configuration

signal = 2;
noise = 0; % in percentage
 

%% Initialize Workspace for Brain

% Initial data required for compilation should be initialized
init_vars

% load model and disable fast restart
mdl = 'CSTR_Bonsai';
load_system(mdl);
set_param(mdl, 'FastRestart', 'off');

init_vars

open_system('CSTR_Bonsai')

Cref_signal=signal;

%% Run Brain without noise

sim('CSTR_Bonsai');

tout_b = tout;
simout_b = simout;

%% Run Brain with noise

% Percentage of noise to include
noise_magnitude = noise/100;

% Auxiliary params
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise_magnitude;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise_magnitude;

sim('CSTR_Bonsai');

tout_b_noise = tout;
simout_b_noise = simout;

%% Plot

plot_comparison(tout_b, simout_b,tout_b_noise, simout_b_noise,...
    tout_PI, simout_PI,tout_PI_noise, simout_PI_noise,noise)


%%
function []=plot_comparison(tout_b, simout_b,tout_b_noise, simout_b_noise,...
    tout_PI, simout_PI,tout_PI_noise, simout_PI_noise, noise)

    % Calculate Error RMS of concentration
    metric_rms_C_bench = sqrt(mean((simout_PI(:, 1) - simout_PI(:, 2)).^2));
    metric_rms_C_bench_noise = sqrt(mean((simout_PI_noise(:, 1) - simout_PI_noise(:, 2)).^2));
    metric_rms_C_brain = sqrt(mean((simout_b(:, 1) - simout_b(:, 2)).^2));
    metric_rms_C_brain_noise = sqrt(mean((simout_b_noise(:, 1) - simout_b_noise(:, 2)).^2));
    
    % Calculate percentage improvement of Brain over Benchmark
    improvement = (metric_rms_C_bench - metric_rms_C_brain)/metric_rms_C_bench * 100;
    improvement_noise = (metric_rms_C_bench_noise - metric_rms_C_brain_noise)/metric_rms_C_bench_noise * 100;
    
    % Display % Improvement 
    txt = ['Brain shows' num2str(improvement) '% Improvement over benchmark with no noise']
    txt = ['Brain shows' num2str(improvement_noise) '% Improvement over benchmark with' num2str(noise) 'noise']

    
    % Generate bar graph variables
    x = categorical({'Benchmark', 'Brain'});
    x = reordercats(x, {'Benchmark', 'Brain'});
    y = [metric_rms_C_bench metric_rms_C_brain]; 

    x5 = categorical({'Benchmark', 'Brain'});
    x5 = reordercats(x5, {'Benchmark', 'Brain'});
    y5 = [metric_rms_C_bench_noise metric_rms_C_brain_noise];
    
    % Find max temp reached
    Tmax_bench = max(simout_PI(:,4));
    Tmax_bench_5 = max(simout_PI_noise(:,4));
    Tmax_brain = max(simout_b(:,4));
    Tmax_brain_5 = max(simout_b_noise(:,4));

    % Generate bar graph variables
    xT = categorical({'Benchmark', 'Brain'});
    xT = reordercats(xT, {'Benchmark', 'Brain'});
    yT = [Tmax_bench; Tmax_brain];

    xT5 = categorical({'Benchmark', 'Brain'});
    xT5 = reordercats(xT5, {'Benchmark', 'Brain'});
    yT5 = [Tmax_bench_5; Tmax_brain_5];
    
    figure
    sgtitle('Bonsai Brain vs. Benchmark (Gain Scheduled PI Control)')
    
    % plot results with 0% noise
    subplot(421) 
        plot(tout_b, simout_b(:, 1),'LineStyle','--')
        hold on
        plot(tout_b, simout_b(:, 2),'color','blue')
        plot(tout_PI, simout_PI(:, 2),'color','red')
        hold off
        ylim([0 11])
        legend('Ref', 'Brain','Benchmark','Location','southwest')
        grid, title('0% noise simulated'), ylabel('Residual Concentration (Cr)')

    subplot(423)
        plot(tout_b, simout_b(:, 3),'LineStyle','--')
        hold on
        plot(tout_b, simout_b(:, 4),'color','blue')
        plot(tout_PI, simout_PI(:, 4),'color','red')
        hold off
        ylim([250 450])
        legend('Ref', 'Brain','Benchmark','Location','northwest')
        grid, ylabel('Reactor Temperature (Tr)'), xlabel ('time (s)')
    
    % plot results 5% noise
    subplot(422)
        plot(tout_b_noise, simout_b_noise(:, 1),'LineStyle','--')
        hold on
        plot(tout_b_noise, simout_b_noise(:, 2),'color','blue')
        plot(tout_PI_noise, simout_PI_noise(:, 2),'color','red')
        hold off
        ylim([0 11])
        legend('Ref', 'Brain','Benchmark','Location','southwest')
        grid, title([num2str(noise),'% noise simulated']), ylabel('Residual Concentration (Cr)')

    subplot(424)
        plot(tout_b_noise, simout_b_noise(:, 3),'LineStyle','--')
        hold on
        plot(tout_b_noise, simout_b_noise(:, 4),'color','blue')
        plot(tout_PI_noise, simout_PI_noise(:, 4),'color','red')
        hold off
        ylim([250 450])
        legend('Ref', 'Brain','Benchmark','Location','northwest')
        grid, ylabel('Reactor Temperature (Tr)'), xlabel ('time (s)')
    
    % Plot Error RMS of Cencentration
    subplot(425)
        bar(x,y);
        ylabel('RMS of error'),
        ylim([0 5])

     subplot(426)
         bar(x5,y5)
         ylabel('RMS of error'),
         ylim([0 5])

     % Plot max temp
     subplot(427)
         bar(xT,yT)
         hold on
         yline(400,'LineStyle','--','LineWidth',2)
         title('Max Temperature - 0% noise simulated'),
         ylabel('Reactor Temperature'),
         ylim([0 500])

     subplot(428)
         bar(xT5,yT5)
         hold on
         yline(400,'LineStyle','--','LineWidth',2)
         title(['Max Temperature - ',num2str(noise),'% noise simulated'])
         ylabel('Reactor Temperature'),
         ylim([0 500])

end

