# EVE-NG_Automation

## 1. Déploiement des machines virtuelles
Crée les machines virtuelles sur vSphere et enregistre leurs identifiants dans Vault.

```bash
ansible-playbook playbooks/deploy_rxi_vms.yml --ask-vault-pass
```

## 2. Copie des laboratoires sur les VMs
Transfère les fichiers des laboratoires sur les VMs

```bash
ansible-playbook playbooks/deploy_rxi_lab.yml --ask-vault-pass
```

## 3. Correction des laboratoires
Analyse les fichiers soumis par les étudiants et génère des rapports de correction

```bash
ansible-playbook playbooks/lab_correction.yml
```
