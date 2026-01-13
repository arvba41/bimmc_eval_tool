%% Set-up for the optimization probelm
clear all

% load DataBuffer.mat; % loading the file from the dashboard.

% Uncomment th e following line if you want to run the optimizer exteranlly
load Parameters_dashboard.mat; % loading the parameters input from the user in Dahboard

% Optimization function to optimize the the following variables:
% 1. Energy stored in the submodules
% 2. pulse number

% Function to minimize: the total losses.
%% Constraints
global f_didt_min Ecap_vector_sweep p_vector_sweep Enable_cons Rth_pad_mtx Psc_tot_avg Pbatt_avg_tot Pcap_avg_tot
f_didt_min = 200e6; % [A/s] minimum allowable didt
Ecap_vector_sweep = logspace(1,log10(100000),100); % SM energy capactior vector 
p_vector_sweep = 1:50; % pulse number sweep
Enable_cons = 0; % 1 - enable constraints, 0 - disable constraints
Rth_pad_mtx = 4.2; % thermal resistance of the pad
LGF = 0.10; % loss gain factor when optimixing the number of parallel MOSFETs 
Params.ccf_lowlim = 0.9; % lower limit for the capacitor current factor

%% Constraints
ConsVars.PbattMax_limit = 10e3; % limit on battery power losses
ConsVars.fall_didtMax_limit = 2000e6; % minimum allowable didt for MOSFETs
ConsVars.CapacitorCurentPeakFactor = 1; % capacitor current factor

%% Evalulation variables (Topology dependent variables)
EvalVars.Nscells = 3;% number of series cells per submodule
EvalVars.Narms = 1; % number of arms 
EvalVars.Nsw = 2; % number of switches per submodule 
EvalVars.Nph_str = '3p'; % type of system (3-phase, 6-phase LV, or 6-phase HV)
EvalVars.Delta = 0; % check for delta topology
% Params.NPmosMin = 2; % minimum number of MOSFETs
% Params.NPmosMax = 20; % minimum number of MOSFETs



%% testing loss gain factor 
NPmosMinMin = 4; % minimum number of parallel MOSFETs choice 
NPmosMinMax = 8; % minimum number of parallel MOSFETs choice 
Params.f_didt_min = f_didt_min;

% initializations 
Params.NPmosMin = NPmosMinMin;
P_loss_total_max_prev = inf;
i = 1;

% while 1
    %% Cost function for DSFB - 5 cells per submodule -- Test case
    [CostVector,P_loss_total_max,Pbatt_max_tot,Pcap_max_tot,Psc_tot_max,Cap_C,NcapC,Cap_Ipk_rating_fact,Cap_Ppk_rating_fact,p_r] = LossMin([],Params,ConsVars,EvalVars);
%     
    P_loss_total(i) = min(P_loss_total_max,[],'all'); % minimum losses
    [m,n] = find(P_loss_total_max == P_loss_total(i)); % find the indices corresponding to minimum losses
%     
    Optim_Ecap(i) = Ecap_vector_sweep(m); % optimal Ecap vector
    Optim_p(i) = p_vector_sweep(n); % optimal_p vector
%     NPmos_vec(i) = Params.NPmosMin + 1; % npmos vector
    
%     if P_loss_total_max_prev <= (1+LGF)*P_loss_total(i) || Params.NPmosMin == NPmosMinMax 
%         break; % get-out of loop
%     end
%     P_loss_total_max_prev = P_loss_total(i); % previous maximum losses results
%     Params.NPmosMin = Params.NPmosMin + 1; % increment the number minimum bumber of parallel MOSFETs
%     i = i + 1; % increment storage index
% end

% plots for the NPMOS optimization 
% figure(1)
% clf
% tiledlayout(3,1)
% 
% % total losses plot
% ax1 = nexttile;
% plot(NPmos_vec,P_loss_total)
% ax1 = figtex(ax1,[]);
% xlabel('$$N_{p,mos}^{min}$$ [-]')
% ylabel('$$P_{loss(tot)}^{max}$$ [W]')
% grid on
% 
% % optimal capcitor energy
% ax2 = nexttile;
% plot(NPmos_vec,Optim_Ecap)
% ax2 = figtex(ax2,[]);
% xlabel('$$N_{p,mos}^{min}$$ [-]')
% ylabel('$$E_{cap(tot)}^{opt}$$ [J]')
% grid on
% 
% % optimal pulse number
% ax3 = nexttile;
% plot(NPmos_vec,Optim_p)
% ax3 = figtex(ax3,[]);
% xlabel('$$N_{p,mos}^{min}$$ [-]')
% ylabel('$$p^{opt}$$ [-]')
% grid on


%% output losses plot

% limits values

figure(1)
clf
% tiledlayout(2,2)

load Camera_Position_EPE.mat

subplot(221)
ax1 = gca;
% surf(ax1,p_vector_sweep*333.333,Ecap_vector_sweep,Pbatt_max_tot/1e3);
[c,h1] = contourf(ax1,p_vector_sweep*333.333,Ecap_vector_sweep,Pbatt_max_tot/1e3);
ax1.ColorScale = 'log';
clabel(c,h1)
cx1 = colorbar;
cx1.Label.Interpreter = 'latex';
cx1.Label.String = '$$P_{batt(tot)}^{max}$$ [kW]';
cx1.TickLabelInterpreter = 'latex';
cx1.FontSize = 12;
cx1.Ticks = [0 2 4 6 8 10 15 20 40];
h1.LevelList = [0 2 4 6 8 10 15 20 40 100];
grid on
ax1 = figtex(ax1,[]);
ax1.LineWidth = 2;
ax1.FontSize = 12;
% ax1.ZScale = 'log';
ylabel('$$E_{cap(tot)}$$ [J]')
xlabel('$$f_{sw}$$ [Hz]')
zlabel('$$P_{batt(tot)}^{max}$$ [kW]')
clabel(c,h1,'FontSize',12,'Interpreter','latex')
% ax1.CameraPosition = CameraPosotion_EPE_ax1;
% zlim([0 20])
title('Total Battery Losses')
ax1.YTick = [10 100 1000 10000 100000 1000000];
cx1.LineWidth = 2;

subplot(222)
ax2 = gca;
[c,h2] = contourf(ax2,p_vector_sweep*333.333,Ecap_vector_sweep,Pcap_max_tot/1e3);
ax2.ColorScale = 'log';
clabel(c,h2)
h2.LevelList = [0 0.01 0.05 0.1 0.3 0.6 1 2 5 10 50 100];
cx2 = colorbar;
cx2.Label.Interpreter = 'latex';
cx2.Label.String = '$$P_{cap(tot)}^{max}$$ [kW]';
cx2.TickLabelInterpreter = 'latex';
cx2.FontSize = 12;
cx2.Ticks = [0 0.01 0.05 0.1 0.3 0.6 1 2 5 10 50];
grid on
ax2.ColorScale = 'log';
ax2 = figtex(ax2,[]);
ax2.LineWidth = 2;
ax2.ZScale = 'log';
ax2.FontSize = 12;
% ax2.CameraPosition = CameraPosotion_EPE_ax2;
ax2.YTick = [10 100 1000 10000 100000 1000000];
ylabel('$$E_{cap(tot)}$$ [J]')
xlabel('$$f_{sw}$$ [Hz]')
zlabel('$$P_{cap(tot)}^{max}$$ [kW]')
clabel(c,h2,'FontSize',12,'Interpreter','latex')
% zlim([0 20])
title('Total Capacitor Losses')
cx2.LineWidth = 2;

subplot(223)
ax3 = gca;
% ax3 = nexttile;
[c,h3] = contourf(ax3,p_vector_sweep*333.333,Ecap_vector_sweep,squeeze(Psc_tot_max(:,:,1))/1e3);
ax3.ColorScale = 'linear';
clabel(c,h3)
cx3 = colorbar;
cx3.Label.Interpreter = 'latex';
cx3.Label.String = '$$P_{sc(tot)}^{max}$$ [kW]';
cx3.TickLabelInterpreter = 'latex';
cx3.FontSize = 12;
cx3.Ticks = h3.LevelList(2:end-1);
grid on
ax3 = figtex(ax3,[]);
ax3.LineWidth = 2;
ax3.ZScale = 'linear';
ax3.FontSize = 12;
% ax3.CameraPosition = CameraPosotion_EPE_ax3;
ylabel('$$E_{cap(tot)}$$ [J]')
xlabel('$$f_{sw}$$ [Hz]')
zlabel('$$P_{conv(tot)}^{max}$$ [kW]')
clabel(c,h3,'FontSize',12,'Interpreter','latex')
title('Total Semiconductor Losses')
ax3.YTick = [10 100 1000 10000 100000 1000000];
cx3.LineWidth = 2;

subplot(224)
ax4 = gca;
% ax4 = nexttile;
[c,h4] = contourf(ax4,p_vector_sweep*333.333,Ecap_vector_sweep,P_loss_total_max/1e3);
ax4.ColorScale = 'log';
clabel(c,h4)
cx4 = colorbar;
cx4.Label.Interpreter = 'latex';
cx4.Label.String = '$$P_{tot}^{max}$$ [kW]';
cx4.TickLabelInterpreter = 'latex';
cx4.FontSize = 12;
cx4.Ticks = [0 2 4 6 8 10 20 40];
ax4 = figtex(ax4,[]);
ax4.LineWidth = 2;
ax4.ZScale = 'log';
ax4.YScale = 'log';
% ax4.CameraPosition = CameraPosotion_EPE_ax4;
ax4.ColorScale = 'log';
ax4.FontSize = 12;
grid on
ylabel('$$E_{cap(tot)}$$ [J]')
xlabel('$$f_{sw}$$ [Hz]')
zlabel('$$P_{loss(tot)}^{max}$$ [kW]')
h4.LevelList = [0 10 15 20 40 60 80 120];
cx4.Ticks = h4.LevelList(2:end-1);
clabel(c,h4,'FontSize',12,'Interpreter','latex')
title('Total Losses')
ax4.YTick = [10 100 1000 10000 100000 1000000];
cx4.LineWidth = 2;

figure(2)
clf
tiledlayout(2,2)

ax5 = nexttile;
[c,h] = contourf(ax5,p_vector_sweep*333.333,Ecap_vector_sweep,squeeze(Cap_C(:,:,1))/1e-3);
clabel(c,h)
colorbar

grid on
ylabel('E_{cap(tot)} [J]')
xlabel('f_{sw} [Hz]')
zlabel('C_{cap} [mF]')

ax6 = nexttile;
surf(ax6,p_vector_sweep*333.333,Ecap_vector_sweep,squeeze(NcapC(:,:,1)))
grid on
ylabel('E_{cap(tot)} [J]')
xlabel('f_{sw} [Hz]')
zlabel('N_{cap} [-]')
% ,Cap_Ppk_rating_fact,p_r

ax7 = nexttile;
surf(ax7,p_vector_sweep*333.333,Ecap_vector_sweep,squeeze(Cap_Ipk_rating_fact(:,:,1)))
hold on
mesh(ax7,p_vector_sweep*333.333,Ecap_vector_sweep,ones(length(Ecap_vector_sweep),length(p_vector_sweep*333.333)),'FaceAlpha','0.3','EdgeColor','r')
grid on
ylabel('E_{cap(tot)} [J]')
xlabel('f_{sw} [Hz]')
zlabel('\beta_f [-]')

ax8 = nexttile;
global NoofParallel_actiVe_mosfets
[c,h] = contourf(ax8,p_vector_sweep*333.333,Ecap_vector_sweep,squeeze(NoofParallel_actiVe_mosfets(:,:,1)));
clabel(c,h);
colorbar
grid on
ylabel('E_{cap(tot)} [J]')
xlabel('f_{sw} [Hz]')
zlabel('N_{p,mos} [-]')
ylim([10 500])


% ax9 = nexttile;
% surf(ax9,p_vector_sweep*333.333,Ecap_vector_sweep,squeeze(Cap_Ppk_rating_fact(:,:,1)))
% hold on
% mesh(ax9,p_vector_sweep*333.333,Ecap_vector_sweep,ones(length(Ecap_vector_sweep),length(p_vector_sweep*333.333)),'FaceAlpha','0.3','EdgeColor','r')
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('f_{sw} [Hz]')
% zlabel('\beta_f^P [-]')

ax1.YScale = 'log';
ax2.YScale = 'log';
ax3.YScale = 'log';
ax4.YScale = 'log';
ax5.YScale = 'log';
ax5.ZScale = 'log';
ax6.YScale = 'log';
ax6.ZScale = 'log';
ax7.YScale = 'log';
ax7.ZScale = 'log';
ax8.YScale = 'linear';
ax8.ZScale = 'linear';
% ax9.YScale = 'log';
% ax9.ZScale = 'log';
% linkaxes([ax1 ax2 ax4 ax3 ax5 ax6 ax7 ax8 ax9],'xy')
% linkprop([ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9],{'CameraUpVector'});

% linkprop([ax1, ax2, ax3, ax4],{'CameraUpVector', 'CameraPosition'});
% linkprop([ax7, ax5, ax8, ax6],{'CameraUpVector', 'CameraPosition'});

% Overall minimum 
P_loss_min_5cells = min(P_loss_total_max,[],'all');
[m,n] = find(P_loss_total_max == P_loss_min_5cells);

% Optimal energy for capacitor 
Optimal_Ecap_5cells = Ecap_vector_sweep(m)
Optimal_p_5cells = p_vector_sweep(n)
Optimal_NcapC_5cells = NcapC(m,n,1)
Optimal_Cap_Ipk_rating_fact_5cells = Cap_Ipk_rating_fact(m,n,1)
Optimal_Cap_C_5cells = Cap_C(m,n,1)
Optimal_Cap_Ppk_rating_fact_5cells = Cap_Ppk_rating_fact(m,n,1)
Optimal_p_r_5cells = p_r(m,n,1)


%% Cost function for DSFB - Dynamic-programming-inspired

Enable_cons = 1; % enable constraints 

% Setting up the topologies
Nsw     = [2 4 2 4 4];
Narms   = [2 2 1 1 1];
Delta   = [0 0 0 0 1];

% capacitor under rating factor 
cuf = 0.7:0.1:0.9;

% number of phases
Nph = ["3p" "6l" "6h"];

tic
% j = 2;
% i = 6; % test
for k = 1:length(Nph)
for j = 1:length(Nsw) % number of topologies loop
for i = 1:12 % Number of cells loop
    for z = 1:length(cuf)

Ecap_vector_sweep = logspace(1,log10(i*1000),100); % SM energy capactior vector 
% The resonance occurs at different Energiers for different number of
% cascaded cells 
p_vector_sweep = 1:50; % pulse number sweep    

%%% Evalulation variables (Topology dependent variables)
EvalVars.Nscells = i;% number of series cells per submodule
EvalVars.Narms = Narms(j); % number of arms 
EvalVars.Nsw = Nsw(j); % number of switches per submodule 
EvalVars.Nph_str = Nph(k); % type of system (3-phase, 6-phase LV, or 6-phase HV)
EvalVars.Delta = Delta(j); % check for delta topology
Params.ccf_lowlim = cuf(z); % capcitor under-rating factor

[CostVector,P_loss_total_max,Pbatt_max_tot,Pcap_max_tot,Psc_tot_max,Cap_C,NcapC,Cap_Ipk_rating_fact,Cap_Ppk_rating_fact,p_r] = LossMin([],Params,ConsVars,EvalVars);

% output losses plot
% figure((j-1)*100+i)
% clf
% tiledlayout(3,3)
% 
% ax1 = nexttile;
% surf(p_vector_sweep,Ecap_vector_sweep,Pbatt_max_tot/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{batt(tot)}^{max} [kW]')
% % zlim([0 20])
% 
% ax2 = nexttile;
% surf(p_vector_sweep,Ecap_vector_sweep,Pcap_max_tot/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{cap(tot)}^{max} [kW]')
% % zlim([0 20])
% 
% ax3 = nexttile;
% surf(p_vector_sweep,Ecap_vector_sweep,squeeze(Psc_tot_max(:,:,1))/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{conv(tot)}^{max} [kW]')
% 
% ax4 = nexttile([2 3]);
% surf(p_vector_sweep,Ecap_vector_sweep,P_loss_total_max/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{loss(tot)}^{max} [kW]')
% 
% ax1.YScale = 'log';
% ax2.YScale = 'log';
% ax3.YScale = 'log';
% ax4.YScale = 'log';
% linkaxes([ax1 ax2 ax4 ax3],'xy')
% linkprop([ax1, ax2, ax3, ax4],{'CameraUpVector', 'CameraPosition'});
% 
% Overall minimum 
P_loss_min_vector(j,i,k,z) = min(P_loss_total_max,[],'all');
[m,n] = find(P_loss_total_max == P_loss_min_vector(j,i,k,z));

% Optimal energy for capacitor 
Optimal_Ecap_vector(j,i,k,z) = Ecap_vector_sweep(m);
Optimal_p_vector(j,i,k,z) = p_vector_sweep(n);

Optimal_NcapC_vector(j,i,k,z) = NcapC(m,n,1);
Optimal_Cap_Ipk_rating_fact_vector(j,i,k,z) = Cap_Ipk_rating_fact(m,n,1);
Optimal_Cap_C_vector(j,i,k,z) = Cap_C(m,n,1);
Optimal_Cap_Ppk_rating_fact_vector(j,k,i,z) = Cap_Ppk_rating_fact(m,n,1);
Optimal_p_r_vector(j,i,k,z) = p_r(m,n,1);

Pcap_avg_tot_optim(j,i,k,z) = Psc_tot_avg(m,n);
Pbatt_avg_tot_optim(j,i,k,z) = Pbatt_avg_tot(m,n,1);
Pcap_avg_tot_optim(j,i,k,z) = Pcap_avg_tot(m,n,1);

    end
end
end
end

toc 

%% Plots
figure(101)
clf

% first plot
%%% 3phase system
subplot(3,3,1)
plot(1:12,squeeze(P_loss_min_vector(:,:,1))/1e3)
grid on
ylabel('P_{loss(tot)}^{max} [kW]')
xlabel('N_{s,cells}')
title('3-phase system')

legend('DSHB','DSFB','SSHB','SSFB','SDFB')

subplot(3,3,4)
plot(1:12,squeeze(Optimal_Ecap_vector(:,:,1)))
grid on
ylabel('E_{cap(tot)}^{opt} [J]')
xlabel('N_{s,cells}')

subplot(3,3,7)
plot(1:12,squeeze(Optimal_p_vector(:,:,1)))
grid on
ylabel('p^{opt} [-]')
xlabel('N_{s,cells}')

%%% 6phase LV system
subplot(3,3,2)
plot(1:12,squeeze(P_loss_min_vector(:,:,2))/1e3)
grid on
ylabel('P_{loss(tot)}^{max} [kW]')
xlabel('N_{s,cells}')
title('6-phase LV system')

% legend('DSHB','DSFB','SSHB','SSFB','SDFB')

subplot(3,3,5)
plot(1:12,squeeze(Optimal_Ecap_vector(:,:,2)))
grid on
ylabel('E_{cap(tot)}^{opt} [J]')
xlabel('N_{s,cells}')

subplot(3,3,8)
plot(1:12,squeeze(Optimal_p_vector(:,:,2)))
grid on
ylabel('p^{opt} [-]')
xlabel('N_{s,cells}')

%%% 6phase HV system
subplot(3,3,3)
plot(1:12,squeeze(P_loss_min_vector(:,:,3))/1e3)
grid on
ylabel('P_{loss(tot)}^{max} [kW]')
xlabel('N_{s,cells}')
title('6-phase HV system')

% legend('DSHB','DSFB','SSHB','SSFB','SDFB')

subplot(3,3,6)
plot(1:12,squeeze(Optimal_Ecap_vector(:,:,3)))
grid on
ylabel('E_{cap(tot)}^{opt} [J]')
xlabel('N_{s,cells}')

subplot(3,3,9)
plot(1:12,squeeze(Optimal_p_vector(:,:,3)))
grid on
ylabel('p^{opt} [-]')
xlabel('N_{s,cells}')


% second plot
figure(102)
clf

%%% 3 phase system 
subplot(3,3,1)
plot(1:12,squeeze(Optimal_NcapC_vector(:,:,1)))
grid on
ylabel('N_{cap(sm)}^{opt} [-]')
xlabel('N_{s,cells}')
title('3-phase system')

subplot(3,3,4)
plot(1:12,squeeze(Optimal_Cap_Ipk_rating_fact_vector(:,:,1)))
grid on
ylabel('\gamma_{cap(sm)}^{opt} [-]')
xlabel('N_{s,cells}')

subplot(3,3,7)
plot(1:12,squeeze(Optimal_Cap_C_vector(:,:,1))/1e-3)
grid on
ylabel('C_{sm}^{opt} [mF]')
xlabel('N_{s,cells}')

legend('DSHB','DSFB','SSHB','SSFB','SDFB')

%%% 6 phase LV system 
subplot(3,3,2)
plot(1:12,squeeze(Optimal_NcapC_vector(:,:,2)))
grid on
ylabel('N_{cap(sm)}^{opt} [-]')
xlabel('N_{s,cells}')
title('6-phase LV system')

subplot(3,3,5)
plot(1:12,squeeze(Optimal_Cap_Ipk_rating_fact_vector(:,:,2)))
grid on
ylabel('\gamma_{cap(sm)}^{opt} [-]')
xlabel('N_{s,cells}')

subplot(3,3,8)
plot(1:12,squeeze(Optimal_Cap_C_vector(:,:,2))/1e-3)
grid on
ylabel('C_{sm}^{opt} [mF]')
xlabel('N_{s,cells}')

%%% 6 phase HV system 
subplot(3,3,3)
plot(1:12,squeeze(Optimal_NcapC_vector(:,:,3)))
grid on
ylabel('N_{cap(sm)}^{opt} [-]')
xlabel('N_{s,cells}')
title('6-phase HV system')

subplot(3,3,6)
plot(1:12,squeeze(Optimal_Cap_Ipk_rating_fact_vector(:,:,3)))
grid on
ylabel('\gamma_{cap(sm)}^{opt} [-]')
xlabel('N_{s,cells}')

subplot(3,3,9)
plot(1:12,squeeze(Optimal_Cap_C_vector(:,:,3))/1e-3)
grid on
ylabel('C_{sm}^{opt} [mF]')
xlabel('N_{s,cells}')

%% Optimizer

%%% initial conditions 
% x0 = [350 13]; % x(1) -- Total energy stored in SM capacitor
    % x(2) -- pulse number  

%%% Cost function
% [CostVector] = LossMin(x0,10e3,200,5,2,4,0,1,3,20);

% %%%% Optimizer settings 
% options = optimoptions('fmincon');
% % options.FiniteDifferenceStepSize = 1; % step tolerance for optimization variable
% options.DiffMinChange = 1; % minimum step size change
% 
% %%%% FMINCON
% tic
% [x,fval,exitflag,output,lambda,grad,hessian] = fmincon(@(x) LossMin(x,10e3,200,5,2,4,0,1,3,20),x0,[],[],[],[],[10 1],[1e4 50],[],options);
% toc
