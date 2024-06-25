# Generated by Django 4.2.11 on 2024-06-25 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0001_squashed_0005_rename_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='searchidentifier',
            name='searchableResourceType',
            field=models.CharField(choices=[('A', 'Audiovisual'), ('B', 'Book'), ('Bc', 'BookChapter'), ('C', 'Collection'), ('Cn', 'ComputationalNotebook'), ('Cp', 'ConferencePaper'), ('Cr', 'ConferenceProceeding'), ('Dp', 'DataPaper'), ('D', 'Dataset'), ('Di', 'Dissertation'), ('E', 'Event'), ('Im', 'Image'), ('Is', 'Instrument'), ('In', 'InteractiveResource'), ('J', 'Journal'), ('Ja', 'JournalArticle'), ('M', 'Model'), ('Z', 'Other'), ('O', 'OutputManagementPlan'), ('Pr', 'PeerReview'), ('P', 'PhysicalObject'), ('Pe', 'Preprint'), ('R', 'Report'), ('Se', 'Service'), ('So', 'Software'), ('Su', 'Sound'), ('St', 'Standard'), ('Sr', 'StudyRegistration'), ('T', 'Text'), ('W', 'Workflow')], editable=False, max_length=2),
        ),
    ]
