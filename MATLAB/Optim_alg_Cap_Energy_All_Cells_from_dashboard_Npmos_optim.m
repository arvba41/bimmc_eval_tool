%% Set-up for the optimization probelm
% clear all

% load DataBuffer.mat; % loading the file from the dashboard.

% Uncomment the following line if you want to run the optimizer exteranlly
% load Parameters_dashboard.mat; % loading the parameters input from the user in Dahboard

% Optimization function to optimize the the following variables:
% 1. Energy stored in the submodules
% 2. pulse number

% Function to minimize: the total losses.
%% Constraints
global f_didt_min Ecap_vector_sweep p_vector_sweep Enable_cons Rth_pad_mtx
f_didt_min = 200e6; % [A/s] minimum allowable didt
Ecap_vector_sweep = logspace(1,log10(100000),100); % SM energy capactior vector 
p_vector_sweep = 1:50; % pulse number sweep
Rth_pad_mtx_copy = Rth_pad_mtx; % copy of the Rth_pad_mtx created in the dashboard
% Enable_cons = 0; % 1 - enable constraints, 0 - disable constraints

%% Constraints
ConsVars.PbattMax_limit = 10e3; % limit on battery power losses
ConsVars.fall_didtMax_limit = 200; % minimum allowable didt for MOSFETs
ConsVars.CapacitorCurentPeakFactor = 1; % capacitor current factor

%% Evalulation variables (Topology dependent variables)
% EvalVars.Nscells = 5;% number of series cells per submodule
% EvalVars.Narms = 2; % number of arms 
% EvalVars.Nsw = 4; % number of switches per submodule 
% EvalVars.Nph_str = '3p'; % type of system (3-phase, 6-phase LV, or 6-phase HV)
% EvalVars.Delta = 0; % check for delta topology

%% Cost function for DSFB - 5 cells per submodule -- Test case
% [CostVector,P_loss_total_max,Pbatt_max_tot,Pcap_max_tot,Psc_tot_max,Cap_C,NcapC,Cap_Ipk_rating_fact,Cap_Ppk_rating_fact,p_r] = LossMin([],Params,ConsVars,EvalVars);
% 
%% output losses plot

% limits values
% 
% figure(100)
% clf
% tiledlayout(2,2)
% 
% ax1 = nexttile;
% surf(ax1,p_vector_sweep,Ecap_vector_sweep,Pbatt_max_tot/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{batt(tot)}^{max} [kW]')
% % zlim([0 20])
% 
% ax2 = nexttile;
% surf(ax2,p_vector_sweep,Ecap_vector_sweep,Pcap_max_tot/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{cap(tot)}^{max} [kW]')
% % zlim([0 20])
% 
% ax3 = nexttile;
% surf(ax3,p_vector_sweep,Ecap_vector_sweep,squeeze(Psc_tot_max(:,:,1))/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{conv(tot)}^{max} [kW]')
% 
% ax4 = nexttile;
% surf(ax4,p_vector_sweep,Ecap_vector_sweep,P_loss_total_max/1e3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('P_{loss(tot)}^{max} [kW]')
% 
% figure(200)
% clf
% tiledlayout(2,2)
% 
% ax5 = nexttile;
% surf(ax5,p_vector_sweep,Ecap_vector_sweep,squeeze(Cap_C(:,:,1))/1e-3)
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('C_{cap} [mF]')
% 
% ax6 = nexttile;
% surf(ax6,p_vector_sweep,Ecap_vector_sweep,squeeze(NcapC(:,:,1)))
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('N_{cap} [-]')
% % ,Cap_Ppk_rating_fact,p_r
% 
% ax7 = nexttile;
% surf(ax7,p_vector_sweep,Ecap_vector_sweep,squeeze(Cap_Ipk_rating_fact(:,:,1)))
% hold on
% mesh(ax7,p_vector_sweep,Ecap_vector_sweep,ones(length(Ecap_vector_sweep),length(p_vector_sweep)),'FaceAlpha','0.3','EdgeColor','r')
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('\beta_f [-]')
% 
% ax8 = nexttile;
% surf(ax8,p_vector_sweep,Ecap_vector_sweep,squeeze(p_r(:,:,1)))
% grid on
% ylabel('E_{cap(tot)} [J]')
% xlabel('p [-]')
% zlabel('p_{res} [-]')
% 
% % ax9 = nexttile;
% % surf(ax9,p_vector_sweep,Ecap_vector_sweep,squeeze(Cap_Ppk_rating_fact(:,:,1)))
% % hold on
% % mesh(ax9,p_vector_sweep,Ecap_vector_sweep,ones(length(Ecap_vector_sweep),length(p_vector_sweep)),'FaceAlpha','0.3','EdgeColor','r')
% % grid on
% % ylabel('E_{cap(tot)} [J]')
% % xlabel('p [-]')
% % zlabel('\beta_f^P [-]')
% 
% ax1.YScale = 'log';
% ax2.YScale = 'log';
% ax3.YScale = 'log';
% ax4.YScale = 'log';
% ax5.YScale = 'log';
% ax5.ZScale = 'log';
% ax6.YScale = 'log';
% ax6.ZScale = 'log';
% ax7.YScale = 'log';
% ax7.ZScale = 'log';
% ax8.YScale = 'log';
% ax8.ZScale = 'log';
% % ax9.YScale = 'log';
% % ax9.ZScale = 'log';
% % linkaxes([ax1 ax2 ax4 ax3 ax5 ax6 ax7 ax8 ax9],'xy')
% % linkprop([ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9],{'CameraUpVector'});
% 
% % linkprop([ax1, ax2, ax3, ax4],{'CameraUpVector', 'CameraPosition'});
% % linkprop([ax7, ax5, ax8, ax6],{'CameraUpVector', 'CameraPosition'});
% 
% % Overall minimum 
% P_loss_min_5cells = min(P_loss_total_max,[],'all');
% [m,n] = find(P_loss_total_max == P_loss_min_5cells);
% 
% % Optimal energy for capacitor 
% Optimal_Ecap_5cells = Ecap_vector_sweep(m)
% Optimal_p_5cells = p_vector_sweep(n)
% Optimal_NcapC_5cells = NcapC(m,n,1)
% Optimal_Cap_Ipk_rating_fact_5cells = Cap_Ipk_rating_fact(m,n,1)
% Optimal_Cap_C_5cells = Cap_C(m,n,1)
% Optimal_Cap_Ppk_rating_fact_5cells = Cap_Ppk_rating_fact(m,n,1)
% Optimal_p_r_5cells = p_r(m,n,1)
% 

%% Cost function for DSFB - Dynamic-programming-inspired

Enable_cons = 1; % enable constraints 

% Setting up the topologies
% Nsw     = [2 4 2 4 4];
% Narms   = [2 2 1 1 1];
% Delta   = [0 0 0 0 1];
% 
% % number of phases
% Nph = ["3p" "6l" "6h"];

tic
% j = 2;
% i = 6; % test
for k = 1:length(NoofPhases_Names) % number of phases loop
for j = 1:length(Noofswitches_per_sm) % number of topologies loop
for i = 1:length(NoofCells) % Number of cells loop

Ecap_vector_sweep = logspace(1,log10(i*1000),100); % SM energy capactior vector 
% The resonance occurs at different Energiers for different number of
% cascaded cells 
p_vector_sweep = 1:50; % pulse number sweep    

%%% Evalulation variables (Topology dependent variables)
EvalVars.Nscells = NoofCells(i);% number of series cells per submodule
EvalVars.Narms = Noofarms_per_phase(j); % number of arms 
EvalVars.Nsw = Noofswitches_per_sm(j); % number of switches per submodule 
EvalVars.Nph_str = NoofPhases_Names(k); % type of system (3-phase, 6-phase LV, or 6-phase HV)
EvalVars.Delta = Delta(j); % check for delta topology

Rth_pad_mtx = Rth_pad_mtx_copy(j,i,k); % taking individual elemtens from the Rth_pad matrix calculated from the datasheet

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
P_loss_min_vector(j,i,k) = min(P_loss_total_max,[],'all');
[m,n] = find(P_loss_total_max == P_loss_min_vector(j,i,k));

% Optimal energy for capacitor 
Optimal_Ecap_vector(j,i,k) = Ecap_vector_sweep(m);
Optimal_p_vector(j,i,k) = p_vector_sweep(n);

Optimal_NcapC_vector(j,i,k) = NcapC(m,n,1);
Optimal_Cap_Ipk_rating_fact_vector(j,i,k) = Cap_Ipk_rating_fact(m,n,1);
Optimal_Cap_C_vector(j,i,k) = Cap_C(m,n,1);
Optimal_Cap_Ppk_rating_fact_vector(j,k,i) = Cap_Ppk_rating_fact(m,n,1);
Optimal_p_r_vector(j,k,i) = p_r(m,n,1);
end
end
end

toc 

save ('OptimVars_new.mat','Optimal_Cap_C_vector',...
    'Optimal_Cap_Ipk_rating_fact_vector','Optimal_Ecap_vector',...
    'Optimal_NcapC_vector','Optimal_p_vector','Optimal_p_r_vector')
% %% Plots
% figure(101)
% clf
% 
% % first plot
% %%% 3phase system
% subplot(3,3,1)
% plot(1:12,squeeze(P_loss_min_vector(:,:,1))/1e3)
% grid on
% ylabel('P_{loss(tot)}^{max} [kW]')
% xlabel('N_{s,cells}')
% title('3-phase system')
% 
% legend('DSHB','DSFB','SSHB','SSFB','SDFB')
% 
% subplot(3,3,4)
% plot(1:12,squeeze(Optimal_Ecap_vector(:,:,1)))
% grid on
% ylabel('E_{cap(tot)}^{opt} [J]')
% xlabel('N_{s,cells}')
% 
% subplot(3,3,7)
% plot(1:12,squeeze(Optimal_p_vector(:,:,1)))
% grid on
% ylabel('p^{opt} [-]')
% xlabel('N_{s,cells}')
% 
% %%% 6phase LV system
% subplot(3,3,2)
% plot(1:12,squeeze(P_loss_min_vector(:,:,2))/1e3)
% grid on
% ylabel('P_{loss(tot)}^{max} [kW]')
% xlabel('N_{s,cells}')
% title('6-phase LV system')
% 
% % legend('DSHB','DSFB','SSHB','SSFB','SDFB')
% 
% subplot(3,3,5)
% plot(1:12,squeeze(Optimal_Ecap_vector(:,:,2)))
% grid on
% ylabel('E_{cap(tot)}^{opt} [J]')
% xlabel('N_{s,cells}')
% 
% subplot(3,3,8)
% plot(1:12,squeeze(Optimal_p_vector(:,:,2)))
% grid on
% ylabel('p^{opt} [-]')
% xlabel('N_{s,cells}')
% 
% %%% 6phase HV system
% subplot(3,3,3)
% plot(1:12,squeeze(P_loss_min_vector(:,:,3))/1e3)
% grid on
% ylabel('P_{loss(tot)}^{max} [kW]')
% xlabel('N_{s,cells}')
% title('6-phase HV system')
% 
% % legend('DSHB','DSFB','SSHB','SSFB','SDFB')
% 
% subplot(3,3,6)
% plot(1:12,squeeze(Optimal_Ecap_vector(:,:,3)))
% grid on
% ylabel('E_{cap(tot)}^{opt} [J]')
% xlabel('N_{s,cells}')
% 
% subplot(3,3,9)
% plot(1:12,squeeze(Optimal_p_vector(:,:,3)))
% grid on
% ylabel('p^{opt} [-]')
% xlabel('N_{s,cells}')
% 
% 
% % second plot
% figure(102)
% clf
% 
% %%% 3 phase system 
% subplot(3,3,1)
% plot(1:12,squeeze(Optimal_NcapC_vector(:,:,1)))
% grid on
% ylabel('N_{cap(sm)}^{opt} [-]')
% xlabel('N_{s,cells}')
% title('3-phase system')
% 
% subplot(3,3,4)
% plot(1:12,squeeze(Optimal_Cap_Ipk_rating_fact_vector(:,:,1)))
% grid on
% ylabel('\gamma_{cap(sm)}^{opt} [-]')
% xlabel('N_{s,cells}')
% 
% subplot(3,3,7)
% plot(1:12,squeeze(Optimal_Cap_C_vector(:,:,1))/1e-3)
% grid on
% ylabel('C_{sm}^{opt} [mF]')
% xlabel('N_{s,cells}')
% 
% legend('DSHB','DSFB','SSHB','SSFB','SDFB')
% 
% %%% 6 phase LV system 
% subplot(3,3,2)
% plot(1:12,squeeze(Optimal_NcapC_vector(:,:,2)))
% grid on
% ylabel('N_{cap(sm)}^{opt} [-]')
% xlabel('N_{s,cells}')
% title('6-phase LV system')
% 
% subplot(3,3,5)
% plot(1:12,squeeze(Optimal_Cap_Ipk_rating_fact_vector(:,:,2)))
% grid on
% ylabel('\gamma_{cap(sm)}^{opt} [-]')
% xlabel('N_{s,cells}')
% 
% subplot(3,3,8)
% plot(1:12,squeeze(Optimal_Cap_C_vector(:,:,2))/1e-3)
% grid on
% ylabel('C_{sm}^{opt} [mF]')
% xlabel('N_{s,cells}')
% 
% %%% 6 phase HV system 
% subplot(3,3,3)
% plot(1:12,squeeze(Optimal_NcapC_vector(:,:,3)))
% grid on
% ylabel('N_{cap(sm)}^{opt} [-]')
% xlabel('N_{s,cells}')
% title('6-phase HV system')
% 
% subplot(3,3,6)
% plot(1:12,squeeze(Optimal_Cap_Ipk_rating_fact_vector(:,:,3)))
% grid on
% ylabel('\gamma_{cap(sm)}^{opt} [-]')
% xlabel('N_{s,cells}')
% 
% subplot(3,3,9)
% plot(1:12,squeeze(Optimal_Cap_C_vector(:,:,3))/1e-3)
% grid on
% ylabel('C_{sm}^{opt} [mF]')
% xlabel('N_{s,cells}')

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
