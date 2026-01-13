%% Version 1
% % Change in the peak RMS current as the numnber of cells per submodule
% % increases
% Icap_pk_relation_wrt_NoofCelss = [1 0.9131 0.8338 0.7613 0.6951 0.6347 0.5796 0.5292 0.4832 0.4412 0.4029 0.3679];
% % MOSFET 'on'-state resistance
% MOSFET_Rdson = [2.5e-4 4e-4 4e-4 4e-4 4e-4 4e-4 6.8e-4 6.8e-4 6.8e-4 1.05e-3 1.05e-3 1.05e-3];
% % MOSFET junction to case thermal resistance
% MOSFET_Rthja = [1.4 1.2 1.2 0.61 0.61 0.61 0.5 0.5 0.5 0.48 0.48 0.48];
% % MOSFET cost [€]
% MOSFET_cost = [3 3 3 3 3 3 3 3 3 3 3 3];
% M = [Icap_pk_relation_wrt_NoofCelss; MOSFET_Rdson; MOSFET_Rthja; MOSFET_cost];
% 
% writematrix(M,'Vector_params.txt')

%% Version 2

% Change in the peak RMS current as the numnber of cells per submodule
% increases
Ccap = [1.00E-03 3.30E-04 1.50E-04 1.00E-04 4.70E-05 3.30E-05];
Vcap = [4 10 16 25 35 50];
ESR = [5.00E-03 5.00E-03 1.50E-02 1.50E-02 1.50E-02 1.50E-02];
Icap = [7 7 4.5 3.3 3.3 3.3];
Lcap = 7.3e-3*ones(size(Vcap)); % Capacitor unit length
Wcap = 4.3e-3*ones(size(Vcap)); % Capacitor unit width
space = 1e-3; % PCB mounting space
Acap = (Lcap+space).*(Wcap+space);
Uc_max = 4;

Ccap_unit = interp1(Vcap,Ccap,Uc_max*[1:12],'nearest');
ESR_unit = interp1(Vcap,ESR,Uc_max*[1:12],'nearest');
Icap_unit = interp1(Vcap,Icap,Uc_max*[1:12],'nearest');
Acap_unit = interp1(Vcap,Acap,Uc_max*[1:12],'nearest');
% MOSFET 'on'-state resistance
MOSFET_Rdson = [2.5e-4 4e-4 4e-4 4e-4 4e-4 4e-4 6.8e-4 6.8e-4 6.8e-4 1.05e-3 1.05e-3 1.05e-3];
% MOSFET junction to case thermal resistance
MOSFET_Rthja = [1.4 1.2 1.2 0.61 0.61 0.61 0.5 0.5 0.5 0.48 0.48 0.48];
% MOSFET cost [€]
MOSFET_cost = [3 3 3 3 3 3 3 3 3 3 3 3];

Log_rate = [1 0.9131 0.8338 0.7613 0.6951 0.6347 0.5796 0.5292 0.4832 0.4412 0.4029 0.3679];

M = [Log_rate; Ccap_unit; ESR_unit; Icap_unit; Acap_unit; MOSFET_Rdson; MOSFET_Rthja; MOSFET_cost];

writematrix(M,'Vector_params.txt')

load OptimVars.mat % load optimized values of energy and pulse numbers for all topologies
