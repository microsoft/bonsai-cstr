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
    disp(['Brain shows ' num2str(improvement) '% Improvement over gain-scheduled PI control with 0% noise'])
    disp(['Brain shows ' num2str(improvement_noise) '% Improvement over gain-scheduled PI control with ' num2str(noise) '% noise'])

    
    % Generate bar graph variables
    x = categorical({'PI', 'Brain'});
    x = reordercats(x, {'PI', 'Brain'});
    y = [metric_rms_C_bench metric_rms_C_brain]; 

    x5 = categorical({'PI', 'Brain'});
    x5 = reordercats(x5, {'PI', 'Brain'});
    y5 = [metric_rms_C_bench_noise metric_rms_C_brain_noise];
    
    % Find max temp reached
    Tmax_bench = max(simout_PI(:,4));
    Tmax_bench_5 = max(simout_PI_noise(:,4));
    Tmax_brain = max(simout_b(:,4));
    Tmax_brain_5 = max(simout_b_noise(:,4));

    % Generate bar graph variables
    xT = categorical({'PI', 'Brain'});
    xT = reordercats(xT, {'PI', 'Brain'});
    yT = [Tmax_bench; Tmax_brain];

    xT5 = categorical({'PI', 'Brain'});
    xT5 = reordercats(xT5, {'PI', 'Brain'});
    yT5 = [Tmax_bench_5; Tmax_brain_5];
    
    figure
    sgtitle('Bonsai Brain vs. Gain-Scheduled PI Control')
    
    % plot results with 0% noise
    subplot(421) 
        plot(tout_b, simout_b(:, 1),'LineStyle','--')
        hold on
        plot(tout_b, simout_b(:, 2),'color','blue')
        plot(tout_PI, simout_PI(:, 2),'color','red')
        hold off
        ylim([0 11])
        legend('Ref', 'Brain','PI','Location','southwest')
        grid, title('0% noise simulated'), ylabel('Cr (kmol/m^3)')

    subplot(423)
        plot(tout_b, simout_b(:, 3),'LineStyle','--')
        hold on
        plot(tout_b, simout_b(:, 4),'color','blue')
        plot(tout_PI, simout_PI(:, 4),'color','red')
        hold off
        ylim([250 450])
        legend('Ref', 'Brain','PI','Location','northwest')
        grid, ylabel('Tr (K)'), xlabel ('time (s)')
    
    % plot results 5% noise
    subplot(422)
        plot(tout_b_noise, simout_b_noise(:, 1),'LineStyle','--')
        hold on
        plot(tout_b_noise, simout_b_noise(:, 2),'color','blue')
        plot(tout_PI_noise, simout_PI_noise(:, 2),'color','red')
        hold off
        ylim([0 11])
        legend('Ref', 'Brain','PI','Location','southwest')
        grid, title([num2str(noise),'% noise simulated']), ylabel('Cr (kmol/m^3)')

    subplot(424)
        plot(tout_b_noise, simout_b_noise(:, 3),'LineStyle','--')
        hold on
        plot(tout_b_noise, simout_b_noise(:, 4),'color','blue')
        plot(tout_PI_noise, simout_PI_noise(:, 4),'color','red')
        hold off
        ylim([250 450])
        legend('Ref', 'Brain','PI','Location','northwest')
        grid, ylabel('Tr (K)'), xlabel ('time (s)')
    
    % Plot Error RMS of Cencentration
    subplot(425)
        bar(x,y);
        ylabel('RMS of error'),
        title('Cr Error - 0% noise'),
        ylim([0 5])

     subplot(426)
         bar(x5,y5)
         ylabel('RMS of error'),
         title('Cr Error - 5% noise'),
         ylim([0 5])

     % Plot max temp
     subplot(427)
         bar(xT,yT)
         hold on
         yline(400,'LineStyle','--','LineWidth',2)
         title('Max Tr - 0% noise'),
         ylabel('Tr (K)'),
         ylim([0 500])

     subplot(428)
         bar(xT5,yT5)
         hold on
         yline(400,'LineStyle','--','LineWidth',2)
         title(['Max Tr - ',num2str(noise),'% noise'])
         ylabel('Tr (K)'),
         ylim([0 500])

end